from collections.abc import Callable

import plotly.express as px
from django.db.models import (
    Count,
)
from plotly.graph_objects import Figure

from stats.models import Chapter, RefType, TextRef

from .config import DEFAULT_DISCRETE_COLORS, DEFAULT_LAYOUT
from .gallery import ChartGalleryItem, Filetype

type RefTypeTypeChartFunc = Callable[[RefType.Type, ...], Figure]


def rt_type_top_mentions(
    rt_type: type[RefType.Type], first_chapter: Chapter | None = None, last_chapter: Chapter | None = None
) -> Figure:
    """Generic RefType mention count"""
    rt_refs = TextRef.objects.filter(type__type=rt_type)

    if first_chapter:
        rt_refs = rt_refs.filter(chapter_line__chapter__number__gte=first_chapter.number)

    if last_chapter:
        rt_refs = rt_refs.filter(chapter_line__chapter__number__lte=last_chapter.number)

    rt_refs = (
        rt_refs.values("type__name").annotate(rt_instance_cnt=Count("type__name")).order_by("-rt_instance_cnt")[:15]
    )

    rt_refs_count_fig = px.bar(
        rt_refs,
        x="rt_instance_cnt",
        y="type__name",
        color="type__name",
        color_discrete_sequence=DEFAULT_DISCRETE_COLORS,
        text_auto=True,
        labels={"type__name": "Reference name", "rt_instance_cnt": "Mention count"},
    )
    rt_refs_count_fig.update_layout(DEFAULT_LAYOUT)
    rt_refs_count_fig.update_traces(
        textfont={"size": 20},
        textposition="inside",
        showlegend=False,
    )

    return rt_refs_count_fig


def get_reftype_type_gallery(
    rt_type: type[RefType.Type], first_chapter: Chapter | None = None, last_chapter: Chapter | None = None
) -> list[ChartGalleryItem]:
    """Generic top-level gallery for RefType Types"""
    return [
        ChartGalleryItem(
            "Most Mentions",
            "",
            Filetype.SVG,
            lambda: rt_type_top_mentions(rt_type, first_chapter, last_chapter),
            subdir=rt_type.lower(),
        ),
    ]
