from django.db.models import Count, Manager, OuterRef, Subquery, Sum, Window, F
from django.db import connection
import plotly.express as px
from plotly.graph_objects import Figure
from stats.models import RefType, TextRef, Chapter
from .config import DEFAULT_LAYOUT, DEFAULT_DISCRETE_COLORS


def __chapter_counts(rt: RefType):
    """Returns count of [RefType] rt for every chapter _excluding_ those with a zero count"""
    return (
        TextRef.objects.filter(type=rt)
        .order_by("chapter_line__chapter__post_date")
        .values(
            "chapter_line__chapter",
            "chapter_line__chapter__title",
            "chapter_line__chapter__title_short",
        )
        .annotate(count=Count("chapter_line__chapter"))
    )


def __mentions_by_chapter(rt: RefType):
    rt_mentions_subquery = (
        TextRef.objects.filter(type=rt, chapter_line__chapter=OuterRef("id"))
        .values("chapter_line__chapter")
        .annotate(mentions=Count("id"))
        .values("mentions")
    )

    return Chapter.objects.annotate(
        rt_mentions=Subquery(rt_mentions_subquery.values_list("mentions")[:1])
    ).values("title", "number", "rt_mentions", "post_date")


def mentions(rt: RefType) -> Figure:
    rt_mentions_by_chapter = __mentions_by_chapter(rt)

    return px.area(
        rt_mentions_by_chapter,
        x="post_date",
        y="rt_mentions",
        hover_data=["title", "rt_mentions", "post_date"],
        labels=dict(
            title="Chapter",
            rt_mentions="Mentions",
            post_date="Post date",
        ),
    ).update_layout(DEFAULT_LAYOUT)


def cumulative_mentions(rt: RefType) -> Figure:
    cumulative_rt_mentions = __mentions_by_chapter(rt).annotate(
        cum_rt_mentions=Window(expression=Sum("rt_mentions"), order_by="number")
    )

    return px.area(
        cumulative_rt_mentions,
        x="post_date",
        y="cum_rt_mentions",
        hover_data=["title", "cum_rt_mentions", "post_date"],
        labels=dict(
            title="Chapter",
            cum_rt_mentions="Total Mentions",
            post_date="Post date",
        ),
    ).update_layout(DEFAULT_LAYOUT)


def most_mentions_by_chapter(rt: RefType) -> Figure:
    chapter_counts = __chapter_counts(rt)

    title = "Most mentions by chapter"
    if chapter_counts:
        return px.bar(
            chapter_counts.order_by("-count")[:15],
            x="count",
            y="chapter_line__chapter__title_short",
            labels={
                "count": "Mentions",
                "chapter_line__chapter__title_short": "Chapter",
            },
            color="chapter_line__chapter__title_short",
            color_discrete_sequence=DEFAULT_DISCRETE_COLORS,
        ).update_layout(DEFAULT_LAYOUT)
    else:
        return px.bar([], title=title)


def most_mentions_by_book(rt: RefType) -> Figure:
    mentions_by_book = (
        __mentions_by_chapter(rt)
        .values("book")
        .annotate(book_mentions=Sum("rt_mentions"))
        .filter(book_mentions__isnull=False)
        .values("book__title", "book__title_short", "book_mentions")
    )

    if mentions_by_book:
        return px.bar(
            mentions_by_book.order_by("-book_mentions")[:15],
            x="book_mentions",
            y="book__title_short",
            labels={
                "book_mentions": "Mentions",
                "book__title_short": "Book",
                "book__title": "Book (full name)",
            },
            hover_data=["book__title", "book__title_short", "book_mentions"],
            color="book__title_short",
            color_discrete_sequence=DEFAULT_DISCRETE_COLORS,
        ).update_layout(DEFAULT_LAYOUT)
    else:
        return px.bar([], title="Missing data")


def most_mentions_by_volume(rt: RefType) -> Figure:
    mentions_by_volume = (
        __mentions_by_chapter(rt)
        .values("book__volume")
        .annotate(vol_mentions=Sum("rt_mentions"))
        .filter(vol_mentions__isnull=False)
        .values("book__volume__title", "vol_mentions")
    )

    if mentions_by_volume:
        return px.bar(
            mentions_by_volume.order_by("-vol_mentions")[:15],
            x="vol_mentions",
            y="book__volume__title",
            labels={
                "vol_mentions": "Mentions",
                "book__volume__title": "Volume",
            },
            color="book__volume__title",
            color_discrete_sequence=DEFAULT_DISCRETE_COLORS,
        ).update_layout(DEFAULT_LAYOUT)
    else:
        return px.bar([], title="Missing data")
