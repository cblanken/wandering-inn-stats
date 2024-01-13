from django.utils.html import format_html, strip_tags
from django.template.loader import render_to_string
from urllib.parse import quote, urlencode
import django_tables2 as tables
from stats.models import Character, RefType, TextRef


class TextRefTable(tables.Table):
    ref_name: str = tables.Column(accessor="type__name")
    text: str = tables.Column(accessor="chapter_line__text")
    chapter_url: str = tables.Column(
        accessor="chapter_line__chapter__source_url", verbose_name="Chapter"
    )

    class Meta:
        model = TextRef
        template_name = "tables/search_table.html"
        fields = ("ref_name", "text", "chapter_url")

    def render_ref_name(self, record: TextRef):
        if record.type.type == RefType.CHARACTER:
            return render_to_string(
                "patterns/atoms/link/link.html",
                context={
                    "text": f"{record.type.name}",
                    "href": f"https://wiki.wanderinginn.com/{record.type.name}",
                    "external": True,
                },
            )
        elif record.type.type == RefType.CLASS:
            return render_to_string(
                "patterns/atoms/link/link.html",
                context={
                    "text": f"{record.type.name}",
                    "href": f"https://wiki.wanderinginn.com/index.php?title=Special%3ASearch&search=Category%3AClasses+{record.type.name[1:-1]}",
                    "external": True,
                },
            )
        else:
            return record.type.name

    def render_text(self, record: TextRef):
        name = record.type.name
        text = record.chapter_line.text
        first = strip_tags(text[: record.start_column])
        highlight = text[record.start_column : record.end_column]
        last = strip_tags(text[record.end_column :])

        return render_to_string(
            "patterns/atoms/search_result_line/search_result_line.html",
            context={"first": first, "highlight": highlight, "last": last},
        )

    def render_chapter_url(self, record: TextRef, value):
        # Using the full text or a strict character count appears to run into issues when linking
        # with a TextFragment, either with too long URLs or unfinished words
        offset = 25
        fragment_start = (
            record.start_column - offset if record.start_column > offset else 0
        )
        fragment_end = (
            record.end_column + offset
            if len(record.chapter_line.text) > record.end_column + offset
            else len(record.chapter_line.text) - 1
        )
        front_word_cutoff_cnt = 0 if fragment_start == 0 else 1
        end_word_cutoff_cnt = (
            len(record.chapter_line.text)
            if fragment_end == len(record.chapter_line.text) - 1
            else -1
        )

        source_url_with_fragment = f'{value}#:~:text={quote(" ".join(strip_tags(record.chapter_line.text[fragment_start:fragment_end]).split(" ")[front_word_cutoff_cnt:end_word_cutoff_cnt]))}'

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
