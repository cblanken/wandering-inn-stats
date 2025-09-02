from django.db.models import F, QuerySet
from django.urls import NoReverseMatch, reverse
from django.utils.text import slugify
from django.utils.html import strip_tags
from django.utils.safestring import SafeText
from django.template.loader import render_to_string
from urllib.parse import quote
import django_tables2 as tables
from stats.models import Chapter, Character, RefType, TextRef
from typing import Any


EMPTY_TABLE_TEXT = "No results found for the given query"


class TextRefTable(tables.Table):
    ref_name = tables.Column(accessor="type__name", attrs={"th": {"style": "width: 20%;"}})
    text = tables.Column(
        accessor="chapter_line__text",
        attrs={
            "th": {"style": "width: 60%;"},
            "td": {"style": "text-align: justify; padding: 1rem;"},
        },
    )
    chapter_url = tables.Column(
        accessor="chapter_line__chapter__source_url",
        verbose_name="Chapter",
        attrs={"th": {"style": "width: 20%;"}},
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
        model = TextRef
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

    def render_text(self, record: TextRef) -> SafeText:
        text = record.chapter_line.text
        first = strip_tags(text[: record.start_column])
        highlight = text[record.start_column : record.end_column]
        last = strip_tags(text[record.end_column :])

        return render_to_string(
            "patterns/atoms/search_result_line/search_result_line.html",
            context={"first": first, "highlight": highlight, "last": last},
        )

    def render_chapter_url(self, record: TextRef, value) -> SafeText:  # noqa: ANN001
        # Using the full text or a strict character count appears to run into issues when linking
        # with a TextFragment, either with too long URLs or unfinished words
        offset = 25
        fragment_start = record.start_column - offset if record.start_column > offset else 0
        fragment_end = (
            record.end_column + offset
            if len(record.chapter_line.text) > record.end_column + offset
            else len(record.chapter_line.text) - 1
        )
        front_word_cutoff_cnt = 0 if fragment_start == 0 else 1
        end_word_cutoff_cnt = len(record.chapter_line.text) if fragment_end == len(record.chapter_line.text) - 1 else -1

        source_url_with_fragment = f"{value}#:~:text={quote(' '.join(strip_tags(record.chapter_line.text[fragment_start:fragment_end]).split(' ')[front_word_cutoff_cnt:end_word_cutoff_cnt]))}"

        return render_to_string(
            "patterns/atoms/link/link.html",
            context={
                "text": f"{record.chapter_line.chapter.title}",
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


class ReftypeMentionsHtmxTable(tables.Table):
    name = tables.Column(verbose_name="Name", attrs={"th": {"style": "width: 50%"}})
    mentions = tables.Column(verbose_name="Mentions", attrs={"th": {"style": "width: 30%"}})
    word_count = tables.Column(attrs={"th": {"style": "width: 10%"}})
    letter_count = tables.Column(attrs={"th": {"style": "width: 10%"}})

    def render_name(self, _record: RefType, value) -> SafeText:  # noqa: ANN001
        return render_to_string(
            "patterns/atoms/link/stat_link.html",
            context={
                "text": f"{value}",
                "href": f"{slugify(value, allow_unicode=True)}",
            },
        )

    def order_mentions(self, queryset: QuerySet, is_descending: bool) -> tuple[QuerySet[Any], bool]:
        queryset = queryset.annotate(mentions=F("reftypecomputedview__mentions")).order_by(
            F("mentions").desc(nulls_last=True) if is_descending else F("mentions").asc(),
        )

        return (queryset, True)

    class Meta:
        model = RefType
        template_name = "tables/table_partial.html"
        fields = ("name", "mentions", "word_count", "letter_count")
        empty_text = EMPTY_TABLE_TEXT


class CharacterHtmxTable(tables.Table):
    name = tables.Column(
        accessor="ref_type__name",
        verbose_name="Name",
        attrs={"th": {"style": "width: 12rem; max-width: 15rem;"}},
    )
    first_appearance = tables.Column(
        accessor="first_chapter_appearance",
        verbose_name="First appearance",
        attrs={"th": {"style": "width: 12rem; max-width: 15rem;"}},
    )
    wiki = tables.Column(
        accessor="wiki_uri",
        verbose_name="Wiki",
        orderable=False,
        attrs={"th": {"style": "width: 10rem; max-width: 15rem;"}},
    )
    mentions = tables.Column(
        accessor="ref_type__reftypecomputedview__mentions",
        verbose_name="Mentions",
        attrs={"th": {"style": "width: 8rem; max-width: 8rem;"}},
    )

    species = tables.Column(attrs={"th": {"style": "width: 8rem; max-width: 12rem;"}})

    def render_name(self, _record: Character, value: str) -> SafeText:
        return render_to_string(
            "patterns/atoms/link/stat_link.html",
            context={
                "text": f"{value}",
                "href": f"{slugify(value, allow_unicode=True)}",
            },
        )

    def render_first_appearance(self, _record: Character, value) -> SafeText:  # noqa: ANN001
        return render_to_string(
            "patterns/atoms/link/stat_link.html",
            context={
                "text": f"{value.title}",
                "href": reverse("chapters", args=[value.number]),
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
        fields = ("name", "mentions", "species", "first_appearance", "wiki")
        empty_text = EMPTY_TABLE_TEXT


class ChapterHtmxTable(tables.Table):
    title = tables.Column(orderable=False, attrs={"td": {"style": "width: 30%; max-width: 40%;"}})
    number = tables.Column(attrs={"td": {"style": "width: 6rem"}})
    word_count = tables.Column(attrs={"td": {"style": "width: 6rem"}})
    post_date = tables.Column(attrs={"td": {"style": "width: 18rem"}})

    def render_title(self, record: Chapter, value: str) -> SafeText:
        return render_to_string(
            "patterns/atoms/link/stat_link.html",
            context={
                "text": f"{value}",
                "href": reverse("chapters", args=[record.number]),
            },
        )

    class Meta:
        model = Chapter
        template_name = "tables/table_partial.html"
        fields = ("number", "title", "word_count", "post_date")
        empty_text = EMPTY_TABLE_TEXT
