from django.db.models import Count, QuerySet
import plotly.express as px
from plotly.graph_objects import Figure
from stats.models import RefType, TextRef
from .config import DEFAULT_LAYOUT, DEFAULT_DISCRETE_COLORS


def __chapter_counts(rt: RefType) -> QuerySet:
    return (
        TextRef.objects.filter(type=rt)
        .order_by("chapter_line__chapter__post_date")
        .values("chapter_line__chapter__title", "chapter_line__chapter")
        .annotate(count=Count("chapter_line__chapter"))
    )


def histogram(rt: RefType) -> Figure:
    chapter_counts = __chapter_counts(rt)
    return px.histogram(
        chapter_counts,
        title="Total mentions",
        x="chapter_line__chapter__title",
        y="count",
        labels={"chapter_line__chapter__title": "title", "count": "mentions"},
        cumulative=True,
    )


def histogram_cumulative(rt: RefType) -> Figure:
    chapter_counts = __chapter_counts(rt)
    return px.histogram(
        chapter_counts,
        title="Mentions",
        x="chapter_line__chapter__title",
        y="count",
        labels={"chapter_line__chapter__title": "title", "count": "mentions"},
    )


def most_mentions_by_chapter(rt: RefType) -> Figure:
    chapter_counts = __chapter_counts(rt)

    return px.bar(
        chapter_counts.order_by("-count")[:20],
        title="Most mentioned chapters",
        x="chapter_line__chapter__title",
        y="count",
        labels={"count": "mentions", "chapter_line__chapter__title": "title"},
    )
