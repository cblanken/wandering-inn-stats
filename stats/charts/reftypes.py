from django.db.models import Count, QuerySet, OuterRef, Subquery
from django_stubs_ext import ValuesQuerySet
from typing import Any
import plotly.express as px
from plotly.graph_objects import Figure
from stats.models import RefType, TextRef, Chapter
from .config import DEFAULT_LAYOUT, DEFAULT_DISCRETE_COLORS


def __chapter_counts_all(rt: RefType):
    """Returns count of [RefType] rt for every chapter _including_ those with a zero count"""
    rt_counts = TextRef.objects.filter(
        type=rt, chapter_line__chapter__id=OuterRef("id")
    ).values("id")
    rt_counts_total = rt_counts.annotate(total=Count("id")).values("total")
    chapters = Chapter.objects.filter(Subquery(rt_counts_total))

    chapters = (
        Chapter.objects.all()
        .order_by("post_date")
        .annotate(
            # count=Subquery(rt_count_sub.annotate(count=Count("id")).values("count")[:1])
            count=Subquery(rt_count_sub.values())
        )
        .values()
    )

    return


def __chapter_counts(rt: RefType):
    """Returns count of [RefType] rt for every chapter _excluding_ those with a zero count"""
    return (
        TextRef.objects.filter(type=rt)
        .order_by("chapter_line__chapter__post_date")
        .values("chapter_line__chapter__title", "chapter_line__chapter")
        .annotate(count=Count("chapter_line__chapter"))
    )


def histogram(rt: RefType) -> Figure:
    chapter_counts = __chapter_counts(rt)

    title = "Mentions"
    if chapter_counts:
        return px.histogram(
            chapter_counts,
            title=title,
            x="chapter_line__chapter__title",
            y="count",
            labels={"chapter_line__chapter__title": "title", "count": "mentions"},
        ).update_layout(DEFAULT_LAYOUT)
    else:
        return px.histogram([], title=title)


def histogram_cumulative(rt: RefType) -> Figure:
    chapter_counts = __chapter_counts(rt)
    title = "Total Mentions"
    if chapter_counts:
        return px.histogram(
            chapter_counts,
            title=title,
            x="chapter_line__chapter__title",
            y="count",
            labels={"chapter_line__chapter__title": "title", "count": "mentions"},
            cumulative=True,
        ).update_layout(DEFAULT_LAYOUT)
    else:
        return px.histogram([], title=title, cumulative=True)


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
