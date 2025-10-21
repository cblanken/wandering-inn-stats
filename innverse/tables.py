from enum import Enum
from typing import Any
from urllib.parse import quote

import django_tables2 as tables
import regex
from django.db.models import F, QuerySet
from django.template.loader import render_to_string
from django.urls import NoReverseMatch, reverse
from django.utils.html import strip_tags
from django.utils.safestring import SafeText
from django.utils.text import slugify

from stats.models import Chapter, ChapterLine, Character, RefType, TextRef

EMPTY_TABLE_TEXT = "No results found"


def highlight_simple_text(text: str, hl: str) -> SafeText:
    return SafeText(
        regex.sub(hl, f'<span class="bg-hl-tertiary text-black p-[1px]">{hl}</span>', text, flags=regex.IGNORECASE)
    )


class RangeType(Enum):
    PHRASE = 0
    KEYWORDS = 1


class WebSearchRange:
    """A range across a search's text indicating a marked phrase OR a section
    containing keywords"""

    type: RangeType
    start: int
    stop: int

    def __init__(self, range_type: RangeType, start: int, stop: int) -> None:
        self.type = range_type
        if start > stop:
            msg = "WebSearch ranges must be ascending."
            raise ValueError(msg)
        self.start = start
        self.stop = stop

    def __repr__(self) -> str:
        return f"<WebSearchRange type: {self.type} start: {self.start}, stop: {self.stop}>"


class WebSearch:
    """Models a Postgres `websearch` query including functions
    for properly highlighting results. The Postgres `websearch` query
    allows for phrases surrounded with qutoes ("), negations with a leading
    minus (-) sign, and keywords for everything else split on whitespace
    - Keywords are normalized to lowercase.
    - Phrases take priority for highlighting, so no keywords should be highlighting
    within phrases.
    - `ignore_range` is a section of the incoming text that is already highlighted or should
    otherwise be ignored when highlighting
    """

    text: str
    text_lower: str
    query: str
    search_ranges: list[WebSearchRange]
    keywords: list[str]
    phrases: list[str]
    negations: list[str]
    max_phrase_highlights: int

    def __init__(self, text: str, query: str, max_phrase_highlights: int = 5) -> None:
        self.text = text
        self.text_lower = text.lower()
        self.query = query
        self.max_phrase_highlights = max_phrase_highlights
        self.keywords, self.phrases, self.negations = self.__parse_query()

    def __parse_query(self) -> tuple[list[str], list[str], list[str]]:
        """Identifies ranges of phrases and keywords from"""
        partitions = self.query.split('"')
        if len(partitions) % 2 == 0:
            # Uneven quotes or no quotes
            msg = "The filter text must contain an even number of quotes to specify any phrases"
            raise ValueError(msg)

        phrases: list[str] = []
        keywords: list[str] = []
        negations: list[str] = []
        if len(partitions) % 2 == 1:
            for i, part in enumerate(partitions):
                if i % 2 == 1:
                    # All odd indexes are quoted phrases
                    phrases.append(part)
                else:
                    for word in regex.split(r"\s+", part):
                        if len(word) > 0:
                            if word[0] == "-":
                                negations.append(word)
                            else:
                                keywords.append(word)

        return (keywords, phrases, negations)

    def __find_text_ranges(self, phrases: list[str]) -> list[WebSearchRange]:
        phrase_ranges: list[WebSearchRange] = []
        for phrase in phrases:
            phrase_highlight_count = 0
            phrase_lookup_start = 0
            while phrase_highlight_count < self.max_phrase_highlights:
                phrase_i = self.text_lower.find(phrase.lower(), phrase_lookup_start)
                if phrase_i == -1:
                    break
                phrase_ranges.append(WebSearchRange(RangeType.PHRASE, phrase_i, phrase_i + len(phrase)))
                phrase_lookup_start = phrase_i + len(phrase)
                phrase_highlight_count += 1

        ranges: list[WebSearchRange] = []
        if phrase_ranges:
            phrase_ranges.sort(key=lambda pr: pr.start)
            keyword_range_start = 0
            for pr in phrase_ranges:
                if keyword_range_start != pr.start:
                    ranges.append(WebSearchRange(RangeType.KEYWORDS, keyword_range_start, pr.start))
                ranges.append(pr)
                keyword_range_start = pr.stop
            if keyword_range_start != len(self.text):
                ranges.append(WebSearchRange(RangeType.KEYWORDS, keyword_range_start, len(self.text)))
        else:
            ranges = [WebSearchRange(RangeType.KEYWORDS, 0, len(self.text))]

        return ranges

    def highlight_range(self, r: WebSearchRange) -> str:
        hl_begin = '<span class="bg-hl-tertiary text-black p-[1px]">'
        hl_end = "</span>"

        match r.type:
            case RangeType.PHRASE:
                return f"{hl_begin}{self.text[r.start : r.stop]}{hl_end}"
            case RangeType.KEYWORDS:
                words = [
                    f"{hl_begin}{word}{hl_end}"
                    if any(regex.match(keyword, word) for keyword in self.keywords)
                    else word
                    for word in regex.split(r"\s+", self.text[r.start : r.stop])
                ]
                return " ".join(words)

    def highlighted_text(self) -> str:
        ranges = self.__find_text_ranges(self.phrases)

        hl_text_sections: list[str] = []
        for r in ranges:
            hl_text_sections.append(self.highlight_range(r))

        return "".join(hl_text_sections)


class SearchQueryTable(tables.Table):
    query: str

    def __init__(self, *args: str, **kwargs: str) -> None:
        super().__init__(*args)
        self.query = kwargs.get("query", "")


class ChapterLineTable(SearchQueryTable):
    """Table for listing chapter lines with direct links to their source"""

    chapter_url = tables.Column(
        accessor="chapter__source_url",
        order_by="number",
        verbose_name="Chapter",
        attrs={"th": {"style": "width: 30%;"}},
    )
    text_plain = tables.Column(
        accessor="text_plain",
        attrs={
            "th": {"style": "width: 70%;"},
            "td": {"style": "text-align: left; min-width: 325px; padding: 8px;"},
        },
        orderable=False,
    )

    class Meta:
        template_name = "tables/table_partial.html"
        empty_text = EMPTY_TABLE_TEXT

    def render_chapter_url(self, record: ChapterLine, value) -> SafeText:  # noqa: ANN001
        # Using the full text or a strict character count appears to run into issues when linking
        # with a TextFragment, either with too long URLs or unfinished words
        source_url_with_fragment = f"{value}#:~:text=" + quote(
            " ".join(regex.split(r"\s", record.text_plain)[:10]).strip()
        )
        return render_to_string(
            "patterns/atoms/link/link.html",
            context={
                "text": f"{record.chapter.title}",
                "href": f"{source_url_with_fragment}",
                "external": True,
            },
        )

    def render_text_plain(self, value) -> SafeText:  # noqa: ANN001, ARG002
        highlighted_text = WebSearch(value, self.query).highlighted_text()
        return SafeText(highlighted_text)


class TextRefTable(SearchQueryTable):
    ref_name = tables.Column(accessor="name", attrs={"th": {"style": "width: 20%;"}})
    text_plain = tables.Column(
        accessor="text_plain",
        attrs={
            "th": {"style": "width: 60%;"},
            "td": {"style": "text-align: left; min-width: 325px; padding: 8px"},
        },
        verbose_name="Text",
        orderable=False,
    )
    chapter_url = tables.Column(
        accessor="source_url",
        order_by="number",
        verbose_name="Chapter",
        attrs={"th": {"style": "width: 20%;"}},
    )

    invalid_filter = regex.compile(r"[<>]")

    @property
    def hidden_cols(self) -> list[int]:
        return self._hidden_cols

    @hidden_cols.setter
    def hidden_cols(self, cols: list[int]) -> None:
        self._hidden_cols = cols

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002 ANN003
        super().__init__(*args, **kwargs)
        self.hidden_cols = []
        if hide_cols := kwargs.get("hidden_cols"):
            self._hidden_cols = hide_cols

    def before_render(self, _request) -> None:  # noqa: ANN001
        for i, col in enumerate(self.columns):
            if i in self._hidden_cols:
                self.columns.hide(col.name)

    class Meta:
        template_name = "tables/table_partial.html"
        fields = ("ref_name", "chapter_url", "text_plain")
        empty_text = EMPTY_TABLE_TEXT

    def render_ref_name(self, record: TextRef, value) -> SafeText | str:  # noqa: ANN001
        try:
            path = f"{record.type.type.lower()}-stats"
            return render_to_string(
                "patterns/atoms/link/stat_link.html",
                context={
                    "text": f"{value}",
                    "href": reverse(path, args=[slugify(value)]),
                },
            )
        except NoReverseMatch:
            return record.type.name

    def render_text_plain(self, record) -> SafeText:  # noqa: ANN001
        ref_text = record.text[record.start_column : record.end_column]
        before = strip_tags(record.text[: record.start_column])
        after = strip_tags(record.text[record.end_column :])
        if self.query and not self.invalid_filter.search(self.query):
            ref_text = highlight_simple_text(ref_text, self.query)

        highlighted_ref = f"<span class='text-hl-primary font-mono font-extrabold'>{ref_text}</span>"
        highlighted_before = WebSearch(before, self.query).highlighted_text()
        highlighted_after = WebSearch(after, self.query).highlighted_text()

        highlighted = highlighted_before + highlighted_ref + highlighted_after
        return SafeText(highlighted)

    def render_chapter_url(self, record, value) -> SafeText:  # noqa: ANN001
        # Using the full text or a strict character count appears to run into issues when linking
        # with a TextFragment, either with too long URLs or unfinished words
        source_url_with_fragment = f"{value}#:~:text=" + quote(
            " ".join(regex.split(r"\s", record.text_plain)[:10]).strip()
        )
        return render_to_string(
            "patterns/atoms/link/link.html",
            context={
                "text": f"{record.title}",
                "href": f"{source_url_with_fragment}",
                "external": True,
            },
        )

    def value_ref_name(self, record: TextRef) -> str:
        return record.type.name

    def value_text_plain(self, record: TextRef) -> str:
        return record.chapter_line.text_plain

    def value_chapter_url(self, record: TextRef) -> str:
        return record.chapter_line.chapter.source_url


class ChapterRefTable(tables.Table):
    ref_name = tables.Column(accessor="name", verbose_name="Name", attrs={"th": {"style": "width: 30%;"}})
    count = tables.Column(accessor="count", verbose_name="Count", attrs={"th": {"style": "width: 10%;"}})
    chapters = tables.Column(
        accessor="chapter_data",
        verbose_name="Chapters",
        attrs={"th": {"style": "width: 60%;"}},
    )

    @property
    def hidden_cols(self) -> list[int]:
        return self._hidden_cols

    @hidden_cols.setter
    def hidden_cols(self, cols: list[int]) -> None:
        self._hidden_cols = cols

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002 ANN003
        super().__init__(*args)
        self._hidden_cols = []
        if hide_cols := kwargs.get("hidden_cols"):
            self._hidden_cols = hide_cols

    def before_render(self, _request) -> None:  # noqa: ANN001
        for i, col in enumerate(self.columns):
            if i in self._hidden_cols:
                self.columns.hide(col.name)

    class Meta:
        template_name = "tables/table_partial.html"
        fields = ("ref_name", "count", "chapters")
        empty_text = EMPTY_TABLE_TEXT

    def render_ref_name(self, record: dict, value) -> SafeText:  # noqa: ANN001
        try:
            path = f"{record['type'].lower()}-stats"
            return render_to_string(
                "patterns/atoms/link/stat_link.html",
                context={
                    "text": f"{value}",
                    "href": reverse(path, args=[slugify(value)]),
                },
            )
        except NoReverseMatch:
            return value

    def render_chapters(self, record) -> str:  # noqa: ANN001
        return ", ".join(
            [
                render_to_string(
                    "patterns/atoms/inline_ref/inline_ref.html",
                    context={
                        "text": f"{chapter[0]}",
                        "href": f"{chapter[1]}",
                    },
                )
                for chapter in record["chapter_data"].order_by("chapter_id")
            ],
        )

    def value_ref_name(self, record) -> str:  # noqa: ANN001
        return record["name"]

    def value_chapters(self, record) -> str:  # noqa: ANN001
        return ";".join([x[1] for x in record["chapter_data"]])


class ReftypeHtmxTable(tables.Table):
    name = tables.Column(verbose_name="Name", attrs={"th": {"style": "width: 30%"}})
    first_mention_num = tables.Column(verbose_name="First mentioned", attrs={"th": {"style": "width: 30%"}})
    mentions = tables.Column(verbose_name="Mentions", attrs={"th": {"style": "width: 15%"}})
    word_count = tables.Column(attrs={"th": {"style": "width: 10%"}})
    letter_count = tables.Column(attrs={"th": {"style": "width: 10%"}})

    def render_name(self, record: RefType) -> SafeText:  # noqa: ANN001
        return render_to_string(
            "patterns/atoms/link/stat_link.html",
            context={
                "text": f"{record.name}",
                "href": f"{slugify(record.name, allow_unicode=True)}",
            },
        )

    def order_mentions(self, queryset: QuerySet, is_descending: bool) -> tuple[QuerySet[Any], bool]:
        queryset = queryset.annotate(mentions=F("reftypecomputedview__mentions")).order_by(
            F("mentions").desc(nulls_last=True) if is_descending else F("mentions").asc(),
        )

        return (queryset, True)

    def render_first_mention_num(self, record) -> SafeText:  # noqa: ANN001
        return render_to_string(
            "patterns/atoms/link/stat_link.html",
            context={
                "text": f"{record.first_mention_title}",
                "href": reverse("chapters", args=[record.first_mention_num]),
            },
        )

    class Meta:
        model = RefType
        template_name = "tables/table_partial.html"
        fields = ("name", "first_mention_num", "mentions", "word_count", "letter_count")
        empty_text = EMPTY_TABLE_TEXT


class CharacterHtmxTable(tables.Table):
    name = tables.Column(
        accessor="ref_type__name",
        verbose_name="Name",
        attrs={"th": {"style": "width: 12rem; max-width: 20%;"}},
    )
    first_appearance = tables.Column(
        accessor="first_chapter_appearance",
        verbose_name="First appearance",
        attrs={"th": {"style": "width: 12rem; max-width: 15%;"}},
    )
    first_mention_num = tables.Column(
        accessor="first_mention_num",
        verbose_name="First mention",
        attrs={"th": {"style": "width: 12rem; max-width: 15%;"}},
    )
    wiki = tables.Column(
        accessor="wiki_uri",
        verbose_name="Wiki",
        orderable=False,
        attrs={"th": {"style": "width: 10rem; max-width: 15%;"}},
    )
    mentions = tables.Column(
        accessor="ref_type__reftypecomputedview__mentions",
        verbose_name="Mentions",
        attrs={"th": {"style": "width: 8rem; max-width: 10%;"}},
    )

    species = tables.Column(attrs={"th": {"style": "width: 8rem; max-width: 10%;"}})

    def render_name(self, record: Character) -> SafeText:
        return render_to_string(
            "patterns/atoms/link/stat_link.html",
            context={
                "text": f"{record.ref_type.name}",
                "href": f"{slugify(record.ref_type.name, allow_unicode=True)}",
            },
        )

    def render_first_appearance(self, value) -> SafeText:  # noqa: ANN001
        return render_to_string(
            "patterns/atoms/link/stat_link.html",
            context={
                "text": f"{value.title}",
                "href": reverse("chapters", args=[value.number]),
            },
        )

    def render_first_mention_num(self, record) -> SafeText:  # noqa: ANN001
        return render_to_string(
            "patterns/atoms/link/stat_link.html",
            context={
                "text": f"{record.first_mention_title}",
                "href": reverse("chapters", args=[record.first_mention_num]),
            },
        )

    def render_wiki(self, record: Character, value) -> SafeText:  # noqa: ANN001
        return render_to_string(
            "patterns/atoms/link/link.html",
            context={
                "text": f"{record.ref_type.name}",
                "href": f"{value}",
                "external": True,
            },
        )

    def order_mentions(self, queryset: QuerySet, is_descending: bool) -> tuple[QuerySet[Any], bool]:
        queryset = queryset.annotate(mentions=F("ref_type__reftypecomputedview__mentions")).order_by(
            F("mentions").desc(nulls_last=True) if is_descending else F("mentions").asc(),
        )

        return (queryset, True)

    def order_first_appearance(self, queryset: QuerySet, is_descending: bool) -> tuple[QuerySet[Any], bool]:
        queryset = queryset.annotate(chapter_num=F("first_chapter_appearance__number")).order_by(
            F("chapter_num").desc(nulls_last=True) if is_descending else F("chapter_num").asc(),
        )

        return (queryset, True)

    class Meta:
        model = Character
        template_name = "tables/table_partial.html"
        fields = ("name", "mentions", "species", "first_appearance", "first_mention_num", "wiki")
        empty_text = EMPTY_TABLE_TEXT


class ChapterHtmxTable(tables.Table):
    title = tables.Column(orderable=False, attrs={"td": {"style": "width: 30%; max-width: 40%;"}})
    number = tables.Column(attrs={"td": {"style": "width: 6rem"}})
    word_count = tables.Column(attrs={"td": {"style": "width: 6rem"}})
    is_canon = tables.Column(attrs={"td": {"style": "width: 4rem"}})
    post_date = tables.Column(attrs={"td": {"style": "width: 10rem"}})
    last_update = tables.Column(verbose_name="Last Updated", attrs={"td": {"style": "width: 10rem"}})

    def render_title(self, record: Chapter, value: str) -> SafeText:
        return render_to_string(
            "patterns/atoms/link/stat_link.html",
            context={
                "text": f"{value}",
                "href": reverse("chapters", args=[record.number]),
            },
        )

    def render_is_canon(self, record: Chapter) -> SafeText:
        yes_no = (
            "<span class='font-bold text-accept'>Yes</span>"
            if record.is_canon
            else "<span class='font-bold text-cancel'>No</span>"
        )
        return SafeText(yes_no)

    class Meta:
        model = Chapter
        template_name = "tables/table_partial.html"
        fields = ("number", "title", "word_count", "is_canon", "post_date", "last_update")
        empty_text = EMPTY_TABLE_TEXT
