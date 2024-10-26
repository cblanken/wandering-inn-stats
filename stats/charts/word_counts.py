from django.db.models import Q, Sum, Func
import plotly.graph_objects as go
from plotly.graph_objects import Figure
import plotly.express as px
import numpy as np
from stats.models import Chapter, Book
from .config import DEFAULT_LAYOUT

chapter_data = (
    Chapter.objects.filter(is_canon=True)
    .values("number", "title", "word_count", "post_date", "book__volume__title")
    .order_by("number")
)


def longest_chapter() -> Chapter:
    chapter_data.order_by("-word_count")[0]


def longest_interlude() -> Chapter:
    chapter_data.filter(is_interlude=True).order_by("-word_count")[0]


def word_count_per_chapter() -> Figure:
    """Word counts per chapter"""
    chapter_wc_fig = px.scatter(
        chapter_data,
        x="number",
        y="word_count",
        hover_data=["title", "number", "word_count", "post_date"],
        trendline="lowess",
        trendline_options=dict(frac=0.2),
        trendline_color_override="#FF8585",
        custom_data=["title", "post_date"],
    )

    chapter_wc_fig.update_layout(
        DEFAULT_LAYOUT,
        xaxis=dict(
            title="Chapter Number", rangeslider=dict(visible=True), type="linear"
        ),
        yaxis=dict(title="Word Count"),
    )

    chapter_wc_fig.data[0]["hovertemplate"] = (
        "<b>Chapter Title</b>: %{customdata[0]}<br>"
        + "<b>Chapter Number</b>: %{x}<br>"
        + "<b>Word Count</b>: %{y}<br>"
        + "<b>Post Date</b>: %{customdata[1]}"
        + "<extra></extra>"
    )

    return chapter_wc_fig


def word_count_cumulative() -> Figure:
    cumulative_chapter_wc = (
        chapter_data.annotate(
            cumsum=Func(
                Sum("word_count"),
                template="%(expressions)s OVER (ORDER BY %(order_by)s)",
                order_by="post_date",
            )
        )
        .values("post_date", "cumsum")
        .order_by("post_date")
    )

    chapter_wc_area = px.area(
        cumulative_chapter_wc,
        x="post_date",
        y="cumsum",
        labels=dict(
            post_date="Post Date",
            word_count="Total Word Count",
        ),
    )

    chapter_wc_area.update_layout(
        DEFAULT_LAYOUT,
        xaxis=dict(title="Post Date"),
        yaxis=dict(title="Total Word Count"),
    )

    return chapter_wc_area


def word_count_authors_note() -> Figure:
    chapter_wc_data = (
        Chapter.objects.filter(authors_note_word_count__gt=0)
        .values("number", "title", "authors_note_word_count")
        .order_by("number")
    )

    chapter_authors_wc_fig = px.line(
        chapter_wc_data,
        x="number",
        y="authors_note_word_count",
        hover_data=["title", "number", "authors_note_word_count"],
        custom_data=["title"],
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
        hovertemplate="<b>Chapter Title</b>: %{customdata[0]}<br>"
        + "<b>Chapter Number</b>: %{x}<br>"
        + "<b>Word Count</b>: %{y}"
        + "<extra></extra>",
    )

    return chapter_authors_wc_fig


def word_count_by_book() -> Figure:
    # Word counts grouped by book
    book_wc_data = (
        Chapter.objects.filter(~Q(book__title__contains="Unreleased"))
        .values(
            "book__volume__title",
            "book",
            "book__title",
            "book__title_short",
            "id",
            "title",
            "word_count",
        )
        .order_by("book", "number")
    )

    book_wc_fig = px.bar(
        book_wc_data,
        x="book__title_short",
        y="word_count",
        color="book__volume__title",
        color_discrete_sequence=px.colors.qualitative.Pastel,
        labels={"book__volume__title": "Volume"},
        hover_data=["title", "book__title", "book__volume__title", "word_count"],
    )

    book_wc_fig.update_layout(
        DEFAULT_LAYOUT,
        xaxis={"title": "Book"},
        yaxis={"title": "Word Count"},
    )

    book_wc_fig.update_traces(
        hovertemplate="<b>Word Count</b>: %{y}<br>"
        + "<b>Chapter</b>: %{customdata[0]}<br>"
        + "<b>Book</b>: %{customdata[1]}<br>"
        + "<b>Volume</b>: %{customdata[2]}<br>"
        + "<extra></extra>",
    )

    return book_wc_fig


def word_count_by_volume() -> Figure:
    volume_wc_data = Chapter.objects.values(
        "book__title",
        "book__title_short",
        "book__volume",
        "book__volume__title",
        "title",
        "word_count",
    ).order_by("book__volume", "number")

    volume_wc_fig = px.bar(
        volume_wc_data,
        x="book__volume__title",
        y="word_count",
        color="book__title",
        color_discrete_sequence=px.colors.qualitative.Pastel,
        labels={"book__title": "Book"},
        hover_data=["title", "book__title", "book__volume__title", "word_count"],
    )
    volume_wc_fig.update_layout(
        DEFAULT_LAYOUT,
        xaxis={
            "title": "Volume",
        },
        yaxis={"title": "Word Count"},
        showlegend=True,
    )
    volume_wc_fig.update_traces(
        hovertemplate="<b>Word Count</b>: %{y}<br>"
        + "<b>Chapter</b>: %{customdata[0]}<br>"
        + "<b>Book</b>: %{customdata[1]}<br>"
        + "<b>Volume</b>: %{x}<br>"
        + "<extra></extra>",
    )

    return volume_wc_fig
