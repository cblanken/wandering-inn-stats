from django.utils.html import format_html, escape, strip_tags
from django.template.loader import render_to_string
from urllib.parse import quote
import django_tables2 as tables
from stats.models import TextRef


class TextRefTable(tables.Table):
    ref_name = tables.Column(accessor="type__name")
    text = tables.Column(accessor="chapter_line__text")
    chapter_url = tables.Column(
        accessor="chapter_line__chapter__source_url", verbose_name="Chapter Source"
    )

    # aliases = [a.name for a in Alias.objects.filter(ref_type__name=ref_name)]

    class Meta:
        model = TextRef
        template_name = "tables/search_table.html"
        fields = ("ref_name", "text", "chapter_url")

    def render_text(self, record):
        name = record.type.name
        text = record.chapter_line.text
        first = text[: record.start_column]
        highlight = text[record.start_column : record.end_column]
        last = text[record.end_column :]

        return render_to_string(
            "patterns/atoms/search_result_line/search_result_line.html",
            context={"first": first, "highlight": highlight, "last": last},
        )

    def render_chapter_url(self, record, value):
        # Using the full text or a strict character count appears to run into issues when linking
        # with a TextFragment, either with too long URLs or unfinished words
        # Fill fragment with next ~8 words
        source_url_with_fragment = f'{value}#:~:text={quote(" ".join(strip_tags(record.chapter_line.text).split(" ")[:8]))}'

        return render_to_string(
            "patterns/atoms/link/link.html",
            context={
                "text": f"{record.chapter_line.chapter.title}",
                "href": f"{source_url_with_fragment}",
                "external": True,
            },
        )
