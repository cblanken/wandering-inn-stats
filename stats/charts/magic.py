from django.db.models import Count
import plotly.express as px
from stats.models import RefType, TextRef
from .config import DEFAULT_LAYOUT, DEFAULT_DISCRETE_COLORS


def spell_ref_counts():
    spell_refs = (
        TextRef.objects.filter(type__type=RefType.SPELL)
        .values("type__name")
        .annotate(spell_instance_cnt=Count("type__name"))
    ).order_by("-spell_instance_cnt")[:15]

    spell_refs_count_fig = px.bar(
        spell_refs,
        x="spell_instance_cnt",
        y="type__name",
        color="type__name",
        color_discrete_sequence=DEFAULT_DISCRETE_COLORS,
        text_auto=True,
        labels=dict(type__name="Spell", spell_instance_cnt="Count"),
    )
    spell_refs_count_fig.update_layout(DEFAULT_LAYOUT)
    spell_refs_count_fig.update_traces(
        textfont=dict(size=20),
        textposition="inside",
        showlegend=False,
    )

    return spell_refs_count_fig
