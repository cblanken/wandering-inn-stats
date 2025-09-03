from django.db.models import Count
import plotly.express as px
from plotly.graph_objects import Figure
from stats.models import RefType, TextRef, Chapter
from .config import DEFAULT_LAYOUT, DEFAULT_DISCRETE_COLORS


def class_ref_counts(first_chapter: Chapter | None = None, last_chapter: Chapter | None = None) -> Figure | None:
    class_refs = TextRef.objects.filter(type__type=RefType.Type.CLASS)

    if first_chapter:
        class_refs = class_refs.filter(chapter_line__chapter__number__gte=first_chapter.number)

    if last_chapter:
        class_refs = class_refs.filter(chapter_line__chapter__number__lte=last_chapter.number)

    class_refs = (
        class_refs.values("type__name")
        .annotate(class_instance_cnt=Count("type__name"))
        .order_by("-class_instance_cnt")[:15]
    )

    class_refs_count_fig = px.bar(
        class_refs,
        x="class_instance_cnt",
        y="type__name",
        color="type__name",
        color_discrete_sequence=DEFAULT_DISCRETE_COLORS,
        text_auto="d",
        labels={"type__name": "Class", "class_instance_cnt": "Count"},
    )
    class_refs_count_fig.update_layout(DEFAULT_LAYOUT)
    class_refs_count_fig.update_traces(
        textfont={"size": 20},
        textposition="inside",
        showlegend=False,
    )

    return class_refs_count_fig
