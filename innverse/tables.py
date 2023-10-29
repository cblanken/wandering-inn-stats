from django.utils.html import format_html, escape, strip_tags
from django.template.loader import render_to_string
from urllib.parse import urlencode
import django_tables2 as tables
from stats.models import TextRef


class TextRefTable(tables.Table):
    ref_name = tables.Column(accessor="type__name")
    text = tables.Column(accessor="chapter_line__text")
    chapter_url = tables.Column(
        accessor="chapter_line__chapter__source_url", verbose_name="Source"
    )

    class Meta:
        model = TextRef
        template_name = "tables/search_table.html"
        fields = ("ref_name", "text", "chapter_url")
        # attrs = {"class": ""}

    def render_chapter_url(self, record, value):
        # Using the full text or a strict character counts appears to run into issues when linking
        # with a TextFragment, either with too long URLs or unfinished words
        # Fill fragment with next ~8 words
        source_url_with_fragment = f'{value}#:~:text={" ".join(strip_tags(record.chapter_line.text).split(" ")[:8])}'

        return render_to_string(
            "patterns/atoms/link/link.html",
            context={
                "text": "LINK",
                "href": f"{source_url_with_fragment}",
                "external": True,
            },
        )
