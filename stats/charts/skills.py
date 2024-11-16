from django.db.models import Count
import plotly.express as px
from plotly.graph_objects import Figure
import numpy as np
from stats.models import RefType, TextRef, Chapter
from .config import DEFAULT_LAYOUT, DEFAULT_DISCRETE_COLORS


def skill_ref_counts(
    first_chapter: Chapter | None, last_chapter: Chapter | None
) -> Figure | None:
    skill_refs = TextRef.objects.filter(type__type=RefType.SKILL)

    if first_chapter:
        skill_refs = skill_refs.filter(
            chapter_line__chapter__number__gte=first_chapter.number
        )

    if last_chapter:
        skill_refs = skill_refs.filter(
            chapter_line__chapter__number__lte=last_chapter.number
        )

    skill_refs = (
        skill_refs.values("type__name")
        .annotate(skill_instance_cnt=Count("type__name"))
        .order_by("-skill_instance_cnt")[:15]
    )

    skill_refs_count_fig = px.bar(
        skill_refs,
        x="skill_instance_cnt",
        y="type__name",
        color="type__name",
        color_discrete_sequence=DEFAULT_DISCRETE_COLORS,
        text_auto=True,
        labels=dict(type__name="Skill", skill_instance_cnt="Count"),
    )
    skill_refs_count_fig.update_layout(DEFAULT_LAYOUT)
    skill_refs_count_fig.update_traces(
        textfont=dict(size=20),
        textposition="inside",
        showlegend=False,
    )

    return skill_refs_count_fig
