from django.db.models import Count, F, Q, Sum, Value, Case, ExpressionWrapper, Min, Max
import plotly.express as px
import numpy as np
import pandas as pd
from enum import Enum
from .models import Chapter, RefType, TextRef, Character


DEFAULT_PLOTLY_TEMPLATE = "plotly_dark"
DEFAULT_HEIGHT = "calc(100vh - 120px)"
DEFAULT_WIDTH = "calc(100vw - 420px)"

DEFAULT_LAYOUT = {
    "font": {
        "family": "Courier New, mono",
        "size": 16,
    },
    "title_font": {
        "family": "Courier New, mono",
        "size": 32,
    },
}


def word_count_charts():
    """Overview charts - all main word count charts to show on overview"""

    # Word counts per chapter
    chapter_wc_data = Chapter.objects.values(
        "number", "title", "word_count", "post_date"
    ).order_by("number")

    chapter_wc_fig = px.scatter(
        chapter_wc_data,
        x="number",
        y="word_count",
        template=DEFAULT_PLOTLY_TEMPLATE,
        hover_data=["title", "number", "word_count", "post_date"],
        trendline="ols",
        trendline_color_override="#FF8585",
    )

    chapter_wc_fig.update_layout(
        DEFAULT_LAYOUT,
        xaxis=dict(
            title="Chapter Number", rangeslider=dict(visible=True), type="linear"
        ),
        yaxis=dict(title="Word Count"),
    )

    chapter_wc_fig.update_traces(
        customdata=np.stack(
            (chapter_wc_data.values_list("title", "post_date"),), axis=-1
        ),
        hovertemplate="<b>Chapter Title</b>: %{customdata[0]}<br>"
        + "<b>Chapter Number</b>: %{x}<br>"
        + "<b>Word Count</b>: %{y}<br>"
        + "<b>Post Date</b>: %{customdata[1]}"
        + "<extra></extra>",
    )

    chapter_wc_html = chapter_wc_fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        default_height=DEFAULT_HEIGHT,
        default_width=DEFAULT_WIDTH,
    )

    # Word counts per author's note
    chapter_wc_data = (
        Chapter.objects.filter(authors_note_word_count__gt=0)
        .values("number", "title", "authors_note_word_count")
        .order_by("number")
    )

    chapter_authors_wc_fig = px.line(
        chapter_wc_data,
        x="number",
        y="authors_note_word_count",
        template=DEFAULT_PLOTLY_TEMPLATE,
        hover_data=["title", "number", "authors_note_word_count"],
    )

    chapter_authors_wc_fig.update_layout(
        DEFAULT_LAYOUT,
        xaxis=dict(
            title="Chapter Number",
            rangeslider=dict(visible=True),
        ),
        yaxis=dict(title="Word Count"),
    )

    chapter_authors_wc_fig.update_traces(
        customdata=np.stack((chapter_wc_data.values_list("title"),), axis=-1),
        hovertemplate="<b>Chapter Title</b>: %{customdata[0]}<br>"
        + "<b>Chapter Number</b>: %{x}<br>"
        + "<b>Word Count</b>: %{y}"
        + "<extra></extra>",
    )

    chapter_authors_wc_html = chapter_authors_wc_fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        default_height=DEFAULT_HEIGHT,
        default_width=DEFAULT_WIDTH,
    )

    # Word counts grouped by book
    book_wc_data = (
        Chapter.objects.filter(~Q(book__title__contains="Unreleased"))
        .values("book", "book__title", "id", "title", "word_count")
        .order_by("book", "number")
    )

    book_wc_fig = px.bar(
        book_wc_data,
        x="book__title",
        y="word_count",
        color="book",
        template=DEFAULT_PLOTLY_TEMPLATE,
        color_continuous_scale=px.colors.qualitative.Vivid,
    )
    book_wc_fig.update_layout(
        DEFAULT_LAYOUT,
        xaxis={"title": "Book"},
        yaxis={"title": "Word Count"},
        showlegend=False,
        coloraxis_showscale=False,
    )

    book_wc_fig.update_traces(
        customdata=np.stack((book_wc_data.values_list("title"),), axis=-1),
        hovertemplate="<b>Book</b>: %{x}<br>"
        + "<b>Chapter</b>: %{customdata[0]}<br>"
        + "<b>Word Count</b>: %{y}"
        + "<extra></extra>",
    )

    book_wc_html = book_wc_fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        default_height=DEFAULT_HEIGHT,
        default_width=DEFAULT_WIDTH,
    )

    # Word counts grouped by volume
    volume_wc_data = Chapter.objects.values(
        "book__volume", "book__volume__title", "id", "title", "word_count"
    ).order_by("book__volume", "number")

    volume_wc_fig = px.bar(
        volume_wc_data,
        x="book__volume__title",
        y="word_count",
        color="book__volume",
        template=DEFAULT_PLOTLY_TEMPLATE,
        color_continuous_scale=px.colors.qualitative.Vivid,
    )
    volume_wc_fig.update_layout(
        DEFAULT_LAYOUT,
        xaxis={"title": "Volume"},
        yaxis={"title": "Word Count"},
        showlegend=False,
        coloraxis_showscale=False,
    )
    volume_wc_fig.update_traces(
        customdata=np.stack((volume_wc_data.values_list("title"),), axis=-1),
        hovertemplate="<b>Volume</b>: %{x}<br>"
        + "<b>Chapter</b>: %{customdata[0]}<br>"
        + "<b>Word Count</b>: %{y}"
        + "<extra></extra>",
    )

    volume_wc_html = volume_wc_fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        default_height=DEFAULT_HEIGHT,
        default_width=DEFAULT_WIDTH,
    )

    return {
        "plots": {
            "Word Counts by Chapter": chapter_wc_html,
            "Word Counts by Volume": volume_wc_html,
            "Word Counts by Book": book_wc_html,
            # "Word Counts by Author's Note": chapter_authors_wc_html,
        },
        "page_title": "Word Counts",
    }


def character_charts():
    """Character stat charts"""

    # Character TextRef counts
    character_text_refs = (
        TextRef.objects.filter(Q(type__type=RefType.CHARACTER))
        .values("type__name")
        .annotate(char_instance_cnt=Count("type__name"))
    )

    if len(character_text_refs) == 0:
        return

    char_refs_count_fig = px.pie(
        character_text_refs,
        names="type__name",
        values="char_instance_cnt",
        template=DEFAULT_PLOTLY_TEMPLATE,
    )
    char_refs_count_fig.update_layout(DEFAULT_LAYOUT)
    char_refs_count_fig.update_traces(
        textposition="inside",
        customdata=np.stack(
            (character_text_refs.values_list("type__name", "char_instance_cnt"),),
            axis=-1,
        ),
        hovertemplate="<b>Character</b>: %{customdata[0][0]}<br>"
        + "<b>Reference Count</b>: %{customdata[0][1]}"
        + "<extra></extra>",
    )
    char_refs_count_html = char_refs_count_fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        default_height=DEFAULT_HEIGHT,
        default_width=DEFAULT_WIDTH,
    )

    char_counts_per_chapter = [
        (
            num,
            TextRef.objects.filter(
                Q(chapter_line__chapter__number=num) & Q(type__type="CH")
            )
            .values("type__name")
            .annotate(cnt=Count("type__name"))
            .count(),
        )
        for num in range(
            TextRef.objects.values().aggregate(
                max=Max("chapter_line__chapter__number")
            )["max"]
        )
    ]

    df = pd.DataFrame(char_counts_per_chapter, columns=["Chapter", "Character Count"])

    # df = pd.DataFrame(char_counts_per_chapter, columns=["Chapter", "Character Count"])
    char_counts_per_chapter_fig = px.scatter(
        df,
        x="Chapter",
        y="Character Count",
        template=DEFAULT_PLOTLY_TEMPLATE,
    )
    char_counts_per_chapter_fig.update_layout(
        DEFAULT_LAYOUT,
        xaxis=dict(
            title="Chapter Number",
            rangeslider=dict(visible=True),
            type="linear",
        ),
        yaxis=dict(title="Character Count"),
    )
    char_counts_per_chapter_fig.update_traces(
        hovertemplate="<b>Chapter</b>: %{x}<br>"
        + "<b>Total Characters</b>: %{y}"
        + "<extra></extra>"
    )
    char_counts_per_chapter_html = char_counts_per_chapter_fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        default_height=DEFAULT_HEIGHT,
        default_width=DEFAULT_WIDTH,
    )

    # Character data counts
    characters = (
        Character.objects.all()
        .annotate(
            species_cnt=Count("species"),
            status_cnt=Count("status"),
        )
        .values()
    )

    # TODO: make this more robust and performant
    # currently scans Character.SPECIES choices tuple to match human-readable string
    for c in characters:
        c["species"] = Character.SPECIES[
            [x[0] for x in Character.SPECIES].index(c["species"])
        ][1]
        c["status"] = Character.STATUSES[
            [x[0] for x in Character.STATUSES].index(c["status"])
        ][1]
        # print(c)

    # Character counts by species
    chars_by_species_fig = px.pie(
        characters,
        names="species",
        values="species_cnt",
        template=DEFAULT_PLOTLY_TEMPLATE,
    )
    chars_by_species_fig.update_layout(DEFAULT_LAYOUT)
    chars_by_species_fig.update_traces(
        textposition="inside",
        customdata=np.stack(
            (characters.values_list("species_cnt", "status_cnt"),), axis=-1
        ),
        hovertemplate="<b>Character Count</b>: %{label}<br>"
        + "<b>Total Characters</b>: %{value}"
        + "<extra></extra>",
    )
    chars_by_species_html = chars_by_species_fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        default_height=DEFAULT_HEIGHT,
        default_width=DEFAULT_WIDTH,
    )

    # Character counts by status
    chars_by_status_fig = px.pie(
        characters,
        names="status",
        values="status_cnt",
        template=DEFAULT_PLOTLY_TEMPLATE,
    )
    chars_by_status_fig.update_layout(DEFAULT_LAYOUT)
    chars_by_status_fig.update_traces(textposition="inside")
    chars_by_status_html = chars_by_status_fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        default_height=DEFAULT_HEIGHT,
        default_width=DEFAULT_WIDTH,
    )

    return {
        "plots": {
            "Character Reference Counts": char_refs_count_html,
            "Unique Characters Per Chapter": char_counts_per_chapter_html,
            "Character Species Counts": chars_by_species_html,
            "Character Status Counts": chars_by_status_html,
        },
        "page_title": "Character Stats",
    }


# Class counts per chapter/book/volume with subplots
def class_charts():
    class_refs = (
        TextRef.objects.filter(type__type=RefType.CLASS)
        .values("type__name")
        .annotate(class_instance_cnt=Count("type__name"))
    )

    if len(class_refs) == 0:
        return

    class_refs_count_fig = px.pie(
        class_refs,
        names="type__name",
        values="class_instance_cnt",
        template=DEFAULT_PLOTLY_TEMPLATE,
    )

    class_refs_count_fig.update_layout(DEFAULT_LAYOUT)
    class_refs_count_fig.update_traces(textposition="inside")
    class_refs_count_fig.update_traces(
        textposition="inside",
        customdata=np.stack(
            (class_refs.values_list("type__name", "class_instance_cnt"),),
            axis=-1,
        ),
        hovertemplate="<b>Class</b>: %{customdata[0][0]}<br>"
        + "<b>Reference Count</b>: %{customdata[0][1]}"
        + "<extra></extra>",
    )

    class_refs_count_html = class_refs_count_fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        default_height=DEFAULT_HEIGHT,
        default_width=DEFAULT_WIDTH,
    )

    return {
        "plots": {
            "Class Reference Counts": class_refs_count_html,
        },
        "page_title": "Class Stats",
    }


# Skill counts per chapter/book/volume with subplots
# Spellcounts per chapter/book/volume with subplots
# Locations counts per chapter/book/volume with subplots
# Item counts per chapter/book/volume with subplots

# isDivine toggle for Classes/Skills/Spells
