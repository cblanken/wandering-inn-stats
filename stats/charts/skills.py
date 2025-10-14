import plotly.express as px
from django.db.models import Count
from plotly.graph_objects import Figure

from stats.models import Chapter, RefType, TextRef

from .config import DEFAULT_DISCRETE_COLORS, DEFAULT_LAYOUT


def skill_ref_counts(first_chapter: Chapter | None, last_chapter: Chapter | None) -> Figure | None:
    skill_refs = TextRef.objects.filter(type__type=RefType.Type.SKILL)

    if first_chapter:
        skill_refs = skill_refs.filter(chapter_line__chapter__number__gte=first_chapter.number)

    if last_chapter:
        skill_refs = skill_refs.filter(chapter_line__chapter__number__lte=last_chapter.number)

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
        labels={"type__name": "Skill", "skill_instance_cnt": "Count"},
    )
    skill_refs_count_fig.update_layout(DEFAULT_LAYOUT)
    skill_refs_count_fig.update_traces(
        textfont={"size": 20},
        textposition="inside",
        showlegend=False,
    )

    return skill_refs_count_fig
