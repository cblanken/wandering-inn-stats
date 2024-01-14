from django.db.models import Q
import plotly.express as px
import numpy as np
from stats.models import Chapter
from .config import DEFAULT_LAYOUT, DEFAULT_PLOTLY_THEME

chapter_wc_data = Chapter.objects.values(
    "number", "title", "word_count", "post_date"
).order_by("number")


def word_count_per_chapter():
    """Word counts per chapter"""
    chapter_wc_fig = px.scatter(
        chapter_wc_data,
        x="number",
        y="word_count",
        template=DEFAULT_PLOTLY_THEME,
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

    return chapter_wc_fig.to_html(
        full_html=False,
        include_plotlyjs=False,
    )


def word_count_histogram():
    sorted_posts = Chapter.objects.order_by("post_date")
    reverse_sorted_posts = Chapter.objects.order_by("-post_date")
    # a ("post_date", ascending=True)
    # first_post = sorted_posts.iloc[0]
    # last_post = sorted_posts.iloc[-1]
    first_post = sorted_posts[0]
    last_post = reverse_sorted_posts[0]

    diff = last_post.post_date - first_post.post_date
    chapter_wc_histogram = px.histogram(
        chapter_wc_data,
        # x="number",
        x="post_date",
        y="word_count",
        nbins=diff.days,
        # nbins=Chapter.objects.all().count(),
        cumulative=True,
        template=DEFAULT_PLOTLY_THEME,
        # hover_data=["title", "number", "word_count", "post_date"],
    )

    # chapter_wc_histogram.update_layout(
    #     DEFAULT_LAYOUT,
    #     xaxis=dict(
    #         title="Chapter Number", rangeslider=dict(visible=True), type="linear"
    #     ),
    #     yaxis=dict(title="Word Count"),
    # )

    return chapter_wc_histogram.to_html(
        full_html=False,
        include_plotlyjs=False,
    )


def word_count_authors_note():
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
        template=DEFAULT_PLOTLY_THEME,
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

    return chapter_authors_wc_fig.to_html(
        full_html=False,
        include_plotlyjs=False,
    )


def word_count_by_book():
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
        template=DEFAULT_PLOTLY_THEME,
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

    return book_wc_fig.to_html(
        full_html=False,
        include_plotlyjs=False,
    )


def word_count_by_volume():
    # Word counts grouped by volume
    volume_wc_data = Chapter.objects.values(
        "book__volume", "book__volume__title", "id", "title", "word_count"
    ).order_by("book__volume", "number")

    volume_wc_fig = px.bar(
        volume_wc_data,
        x="book__volume__title",
        y="word_count",
        color="book__volume",
        template=DEFAULT_PLOTLY_THEME,
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

    return volume_wc_fig.to_html(
        full_html=False,
        include_plotlyjs=False,
    )
