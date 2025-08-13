from django.db.models import Q, Sum, Func
from plotly.graph_objects import Figure
import plotly.express as px
from stats.models import Chapter
from .config import DEFAULT_LAYOUT

chapter_data = Chapter.objects.filter(is_canon=True).order_by("number")


def word_count_per_chapter(first_chapter: Chapter | None = None, last_chapter: Chapter | None = None) -> Figure:
    word_counts = chapter_data
    if first_chapter:
        word_counts = word_counts.filter(number__gte=first_chapter.number)

    if last_chapter:
        word_counts = word_counts.filter(number__lte=last_chapter.number)

    """Word counts per chapter"""
    chapter_wc_fig = px.scatter(
        word_counts.values("word_count", "post_date", "number", "title"),
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
        xaxis=dict(title="Chapter Number", rangeslider=dict(visible=True), type="linear"),
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


def word_count_cumulative(first_chapter: Chapter | None = None, last_chapter: Chapter | None = None) -> Figure:
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

    if first_chapter:
        cumulative_chapter_wc = cumulative_chapter_wc.filter(number__gte=first_chapter.number)

    if last_chapter:
        cumulative_chapter_wc = cumulative_chapter_wc.filter(number__lte=last_chapter.number)

    chapter_wc_area = px.area(
        cumulative_chapter_wc,
        x="post_date",
        y="cumsum",
        labels=dict(
            post_date="Post Date",
            cumsum="Total Word Count",
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


def word_count_by_book(first_chapter: Chapter | None = None, last_chapter: Chapter | None = None) -> Figure:
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

    if first_chapter:
        book_wc_data = book_wc_data.filter(number__gte=first_chapter.number)

    if last_chapter:
        book_wc_data = book_wc_data.filter(number__lte=last_chapter.number)

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


def word_count_by_volume(first_chapter: Chapter | None = None, last_chapter: Chapter | None = None) -> Figure:
    volume_wc_data = (
        Chapter.objects.values("book")
        .annotate(book_word_count=Sum("word_count"))
        .values("book__title", "book_word_count", "book__volume__title")
        .order_by("book__volume__number", "book__number")
    )

    if first_chapter:
        volume_wc_data = volume_wc_data.filter(number__gte=first_chapter.number)

    if last_chapter:
        volume_wc_data = volume_wc_data.filter(number__lte=last_chapter.number)

    volume_wc_fig = px.bar(
        volume_wc_data,
        x="book__volume__title",
        y="book_word_count",
        color="book__title",
        color_discrete_sequence=px.colors.qualitative.Pastel,
        labels={
            "book__title": "Book",
            "book__volume__title": "Volume",
            "book_word_count": "Word count",
        },
        custom_data=["book__title"],
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
        + "<b>Book</b>: %{customdata[0]}<br>"
        + "<b>Volume</b>: %{x}<br>"
        + "<extra></extra>",
    )

    return volume_wc_fig
