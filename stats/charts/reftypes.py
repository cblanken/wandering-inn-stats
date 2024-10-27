from django.db.models import Count, OuterRef, Subquery, Sum, Window
from typing import Any
import plotly.express as px
from plotly.graph_objects import Figure
from stats.models import RefType, TextRef, Chapter
from .config import DEFAULT_LAYOUT, DEFAULT_DISCRETE_COLORS


def __chapter_counts(rt: RefType):
    """Returns count of [RefType] rt for every chapter _excluding_ those with a zero count"""
    return (
        TextRef.objects.filter(type=rt)
        .order_by("chapter_line__chapter__post_date")
        .values("chapter_line__chapter__title", "chapter_line__chapter")
        .annotate(count=Count("chapter_line__chapter"))
    )


def mentions(rt: RefType) -> Figure:
    rt_mentions_subquery = (
        TextRef.objects.filter(type=rt, chapter_line__chapter=OuterRef("id"))
        .values("chapter_line__chapter__id")
        .annotate(mentions=Count("id"))
        .values("mentions")
    )

    rt_mentions_by_chapter = Chapter.objects.annotate(
        rt_mentions=Subquery(rt_mentions_subquery.values_list("mentions")[:1])
    ).values("title", "rt_mentions")

    return px.area(
        rt_mentions_by_chapter,
        x="title",
        y="rt_mentions",
        labels=dict(
            title="Chapter",
            rt_mentions="Mentions",
        ),
    )


def cumulative_mentions(rt: RefType) -> Figure:
    rt_mentions_subquery = (
        TextRef.objects.filter(type=rt, chapter_line__chapter=OuterRef("id"))
        .values("chapter_line__chapter__id")
        .annotate(mentions=Count("id"))
        .values("mentions")
    )

    rt_mentions_by_chapter = Chapter.objects.annotate(
        rt_mentions=Subquery(rt_mentions_subquery.values_list("mentions")[:1])
    ).values("title", "number", "rt_mentions")

    cumulative_rt_mentions = rt_mentions_by_chapter.annotate(
        cumsum=Window(expression=Sum("rt_mentions"), order_by="number")
    )

    return px.area(
        cumulative_rt_mentions,
        x="title",
        y="cumsum",
        labels=dict(
            title="Chapter",
            rt_mentions="Total mentions",
        ),
    )


def most_mentions_by_chapter(rt: RefType) -> Figure:
    chapter_counts = __chapter_counts(rt)

    title = "Most mentions by chapter"
    if chapter_counts:
        return px.bar(
            chapter_counts.order_by("-count")[:20],
            title=title,
            x="chapter_line__chapter__title",
            y="count",
            labels={"count": "mentions", "chapter_line__chapter__title": "title"},
        ).update_layout(DEFAULT_LAYOUT)
    else:
        return px.bar([], title=title)
