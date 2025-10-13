from django.db.models import F, QuerySet
from django.urls import NoReverseMatch, reverse
from django.utils.text import slugify
from django.utils.html import strip_tags, format_html
from django.utils.safestring import SafeText
from django.template.loader import render_to_string
from urllib.parse import quote
import django_tables2 as tables
from stats.models import Chapter, Character, RefType, TextRef, ChapterLine
from typing import Any
import regex

EMPTY_TABLE_TEXT = "No results found"


def highlight_text(text: str, hl: str) -> str:
    return regex.sub(hl, f'<span class="bg-hl-tertiary text-black p-[1px]">{hl}</span>', text, flags=regex.IGNORECASE)


class ChapterLineTable(tables.Table):
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
            "td": {"style": "text-align: justify; padding: 1rem;"},
        },
        orderable=False,
    )

    class Meta:
        template_name = "tables/table_partial.html"
        empty_text = EMPTY_TABLE_TEXT

    def render_chapter_url(self, record: ChapterLine, value) -> SafeText:  # noqa: ANN001
        # Using the full text or a strict character count appears to run into issues when linking
        # with a TextFragment, either with too long URLs or unfinished words
        text_fragment = " ".join(record.text_plain.split(" ")[:10])
        source_url_with_fragment = f"{value}#:~:text={text_fragment}"
        return render_to_string(
            "patterns/atoms/link/link.html",
            context={
                "text": f"{record.chapter.title}",
                "href": f"{source_url_with_fragment}",
                "external": True,
            },
        )

    def render_text_plain(self, record, value) -> SafeText:  # noqa: ANN001
        highlighted_text = format_html(record.headline) if hasattr(record, "headline") else SafeText(value)

        return format_html(highlighted_text)


class TextRefTable(tables.Table):
    ref_name = tables.Column(accessor="name", attrs={"th": {"style": "width: 20%;"}})
    text = tables.Column(
        accessor="text_plain",
        attrs={
            "th": {"style": "width: 60%;"},
            "td": {"style": "text-align: justify; padding: 1rem;"},
        },
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

    @property
    def filter_text(self) -> str | None:
        return self._filter_text

    @filter_text.setter
    def filter_text(self, text: str) -> None:
        self._filter_text = text

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002 ANN003
        super().__init__(*args)
        self._hidden_cols = []
        if hide_cols := kwargs.get("hidden_cols"):
            self._hidden_cols = hide_cols

        self._filter_text = None
        if filter_text := kwargs.get("filter_text"):
            self._filter_text = filter_text

    def before_render(self, _request) -> None:  # noqa: ANN001
        for i, col in enumerate(self.columns):
            if i in self._hidden_cols:
                self.columns.hide(col.name)

    class Meta:
        template_name = "tables/table_partial.html"
        fields = ("ref_name", "chapter_url", "text")
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

    def render_text(self, record) -> SafeText:  # noqa: ANN001
        ref_text = record.text[record.start_column : record.end_column]

        if hasattr(record, "headline"):
            highlighted_text = format_html(record.headline).replace(
                ref_text, f"<span class='text-hl-primary font-mono font-extrabold'>{ref_text}</span>"
            )
        else:
            before = strip_tags(record.text[: record.start_column])
            after = strip_tags(record.text[record.end_column :])
            if self.filter_text and not self.invalid_filter.search(self.filter_text):
                ref_text = highlight_text(ref_text, self.filter_text)
                before = highlight_text(before, self.filter_text)
                after = highlight_text(after, self.filter_text)

            highlighted_text = (
                f"{before}<span class='text-hl-primary font-mono font-extrabold'>{ref_text}</span>{after}"
            )

        return format_html(highlighted_text)

    def render_chapter_url(self, record, value) -> SafeText:  # noqa: ANN001
        # Using the full text or a strict character count appears to run into issues when linking
        # with a TextFragment, either with too long URLs or unfinished words

        offset = 25
        fragment_start = record.start_column - offset if record.start_column > offset else 0
        fragment_end = (
            record.end_column + offset if len(record.text) > record.end_column + offset else len(record.text) - 1
        )
        front_word_cutoff_cnt = 0 if fragment_start == 0 else 1
        end_word_cutoff_cnt = len(record.text) if fragment_end == len(record.text) - 1 else -1

        source_url_with_fragment = f"{value}#:~:text={quote(' '.join(strip_tags(record.text[fragment_start:fragment_end]).split(' ')[front_word_cutoff_cnt:end_word_cutoff_cnt]))}"
        # source_url_with_fragment = f"{value}#:~:text={quote(record.text_plain[:30].strip()).strip()}"

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

    def value_text(self, record: TextRef) -> str:
        return strip_tags(record.chapter_line.text)

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
