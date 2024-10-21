from django.db.models import Q
from plotly.graph_objects import Figure
import plotly.express as px
import numpy as np
from stats.models import Chapter, Book
from .config import DEFAULT_LAYOUT

chapter_data = (
    Chapter.objects.filter(is_canon=True)
    .values("number", "title", "word_count", "post_date")
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
        customdata=np.stack((chapter_data.values_list("title", "post_date"),), axis=-1),
        hovertemplate="<b>Chapter Title</b>: %{customdata[0]}<br>"
        + "<b>Chapter Number</b>: %{x}<br>"
        + "<b>Word Count</b>: %{y}<br>"
        + "<b>Post Date</b>: %{customdata[1]}"
        + "<extra></extra>",
    )

    return chapter_wc_fig


def word_count_histogram() -> Figure:
    sorted_posts = Chapter.objects.order_by("post_date")
    reverse_sorted_posts = Chapter.objects.order_by("-post_date")
    first_post = sorted_posts[0]
    last_post = reverse_sorted_posts[0]

    diff = last_post.post_date - first_post.post_date
    chapter_wc_histogram = px.histogram(
        chapter_data,
        x="post_date",
        y="word_count",
        nbins=diff.days,
        cumulative=True,
        labels=dict(post_date="Post Date", word_count="Total Word Count"),
        hover_data=["title", "number", "word_count", "post_date"],
    )

    chapter_wc_histogram.update_layout(
        DEFAULT_LAYOUT,
        xaxis=dict(title="Post Date"),
        yaxis=dict(title="Total Word Count"),
    )

    return chapter_wc_histogram


def word_count_authors_note() -> Figure:
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

    return chapter_authors_wc_fig


def word_count_by_book() -> Figure:
    # Word counts grouped by book
    book_wc_data = (
        Chapter.objects.filter(~Q(book__title__contains="Unreleased"))
        .values("book", "book__title", "book__title_short", "id", "title", "word_count")
        .order_by("book", "number")
    )

    book_wc_fig = px.bar(
        book_wc_data,
        x="book__title_short",
        y="word_count",
        color="book",
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
        customdata=np.stack(
            (book_wc_data.values_list("title", "book__title"),), axis=-1
        ),
        hovertemplate="<b>Book</b>: %{customdata[1]}<br>"
        + "<b>Chapter</b>: %{customdata[0]}<br>"
        + "<b>Word Count</b>: %{y}"
        + "<extra></extra>",
    )

    return book_wc_fig


def word_count_by_volume() -> Figure:
    # Word counts grouped by volume
    volume_wc_data = Chapter.objects.values(
        "book__volume", "book__volume__title", "id", "title", "word_count"
    ).order_by("book__volume", "number")

    volume_wc_fig = px.bar(
        volume_wc_data,
        x="book__volume__title",
        y="word_count",
        color="book__volume",
        color_continuous_scale=px.colors.qualitative.Vivid,
    )
    volume_wc_fig.update_layout(
        DEFAULT_LAYOUT,
        xaxis={
            "title": "Volume",
        },
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

    return volume_wc_fig
