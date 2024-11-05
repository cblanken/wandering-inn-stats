from django.db.models import Count, Manager, OuterRef, Subquery, Sum, Window, F
from django.db import connection
import plotly.express as px
from plotly.graph_objects import Figure
from stats.models import Book, Chapter, RefType, TextRef, Volume
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
    )


def mentions(rt: RefType) -> Figure | None:
    rt_mentions_by_chapter = __mentions_by_chapter(rt).values(
        "title", "rt_mentions", "post_date"
    )

    if rt_mentions_by_chapter:
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
    else:
        return None


def cumulative_mentions(rt: RefType) -> Figure | None:
    cumulative_rt_mentions = (
        __mentions_by_chapter(rt)
        .annotate(
            cum_rt_mentions=Window(expression=Sum("rt_mentions"), order_by="number")
        )
        .values("title", "cum_rt_mentions", "post_date")
    )

    if cumulative_rt_mentions:
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
    else:
        return None


def most_mentions_by_chapter(rt: RefType) -> Figure | None:
    chapter_counts = __chapter_counts(rt)

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
        return None


def most_mentions_by_book(rt: RefType) -> Figure | None:
    sql = """
    SELECT stats_book.id, "stats_book"."title","stats_book"."title_short", SUM(
         (SELECT COUNT(U0."id") AS "mentions"
          FROM "stats_textref" U0
          INNER JOIN "stats_chapterline" U1 ON (U0."chapter_line_id" = U1."id")
          INNER JOIN "stats_chapter" U2 ON (U1."chapter_id" = U2."id")
          WHERE (U1."chapter_id" = ("stats_chapter"."id")
                 AND U0."type_id" = %s)
          GROUP BY U1."chapter_id"
          LIMIT 1)) AS "book_mentions"
    FROM "stats_chapter"
    INNER JOIN "stats_book" ON ("stats_chapter"."book_id" = "stats_book"."id")
    GROUP BY "stats_book"."id"
    ORDER BY "book_mentions" ASC
    """

    mentions_by_book = [
        b.__dict__ for b in Book.objects.raw(sql, [rt.pk]) if b.book_mentions
    ]

    if mentions_by_book:
        return px.bar(
            mentions_by_book,
            x="book_mentions",
            y="title",
            labels={
                "book_mentions": "Mentions",
                "title_short": "Book",
                "title": "Book (full name)",
            },
            hover_data=["title", "title_short", "book_mentions"],
            orientation="h",
            color="title_short",
            color_discrete_sequence=DEFAULT_DISCRETE_COLORS,
        ).update_layout(DEFAULT_LAYOUT)
    else:
        return None


def most_mentions_by_volume(rt: RefType) -> Figure | None:
    sql = """
    SELECT stats_volume.id, "stats_volume"."title", SUM(
        (SELECT COUNT(U0."id") AS "mentions"
        FROM "stats_textref" U0
        INNER JOIN "stats_chapterline" U1 ON (U0."chapter_line_id" = U1."id")
        INNER JOIN "stats_chapter" U2 ON (U1."chapter_id" = U2."id")
        WHERE (U1."chapter_id" = ("stats_chapter"."id")
             AND U0."type_id" = %s)
        GROUP BY U1."chapter_id"
        LIMIT 1)) AS "vol_mentions"
    FROM "stats_chapter"
    INNER JOIN "stats_book" ON ("stats_chapter"."book_id" = "stats_book"."id")
    INNER JOIN "stats_volume" ON ("stats_book"."volume_id" = "stats_volume"."id")
    GROUP BY "stats_volume"."id"
    ORDER BY "vol_mentions" DESC
    """

    mentions_by_volume = [
        v.__dict__ for v in Volume.objects.raw(sql, [rt.pk]) if v.vol_mentions
    ]

    if mentions_by_volume:
        return px.bar(
            mentions_by_volume,
            x="vol_mentions",
            y="title",
            labels={
                "vol_mentions": "Mentions",
                "title": "Volume",
            },
            orientation="h",
            color="title",
            color_discrete_sequence=DEFAULT_DISCRETE_COLORS,
        ).update_layout(DEFAULT_LAYOUT)
    else:
        return None
