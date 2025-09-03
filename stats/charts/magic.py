from django.db.models import Count
import plotly.express as px
from plotly.graph_objects import Figure
from stats.models import RefType, TextRef, Chapter
from .config import DEFAULT_LAYOUT, DEFAULT_DISCRETE_COLORS


def spell_ref_counts(first_chapter: Chapter | None = None, last_chapter: Chapter | None = None) -> Figure:
    spell_refs = TextRef.objects.filter(type__type=RefType.Type.SPELL)

    if first_chapter:
        spell_refs = spell_refs.filter(chapter_line__chapter__number__gte=first_chapter.number)

    if last_chapter:
        spell_refs = spell_refs.filter(chapter_line__chapter__number__lte=last_chapter.number)

    spell_refs = (
        spell_refs.values("type__name")
        .annotate(spell_instance_cnt=Count("type__name"))
        .order_by("-spell_instance_cnt")[:15]
    )

    spell_refs_count_fig = px.bar(
        spell_refs,
        x="spell_instance_cnt",
        y="type__name",
        color="type__name",
        color_discrete_sequence=DEFAULT_DISCRETE_COLORS,
        text_auto=True,
        labels={"type__name": "Spell", "spell_instance_cnt": "Count"},
    )

    spell_refs_count_fig.update_layout(DEFAULT_LAYOUT)
    spell_refs_count_fig.update_traces(
        textfont={"size": 20},
        textposition="inside",
        showlegend=False,
    )

    return spell_refs_count_fig
