from django.db.models import Count
import plotly.express as px
from stats.models import RefType, TextRef
from .config import DEFAULT_LAYOUT, DEFAULT_DISCRETE_COLORS


def location_ref_counts():
    location_refs = (
        TextRef.objects.filter(type__type=RefType.LOCATION)
        .values("type__name")
        .annotate(location_instance_cnt=Count("type__name"))
    ).order_by("-location_instance_cnt")[:15]

    location_refs_count_fig = px.bar(
        location_refs,
        x="location_instance_cnt",
        y="type__name",
        color="type__name",
        color_discrete_sequence=DEFAULT_DISCRETE_COLORS,
        text_auto=True,
        labels=dict(type__name="location", location_instance_cnt="Count"),
    )
    location_refs_count_fig.update_layout(DEFAULT_LAYOUT)
    location_refs_count_fig.update_traces(
        textfont=dict(size=20),
        textposition="inside",
        showlegend=False,
    )

    return location_refs_count_fig
