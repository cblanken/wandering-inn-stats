from django.db.models import Count
import plotly.express as px
from stats.models import RefType, TextRef
from .config import DEFAULT_LAYOUT, DEFAULT_DISCRETE_COLORS


def class_ref_counts():
    class_refs = (
        TextRef.objects.filter(type__type=RefType.CLASS)
        .values("type__name")
        .annotate(class_instance_cnt=Count("type__name"))
    ).order_by("-class_instance_cnt")[:15]

    class_refs_count_fig = px.bar(
        class_refs,
        x="class_instance_cnt",
        y="type__name",
        color="type__name",
        color_discrete_sequence=DEFAULT_DISCRETE_COLORS,
        text_auto=".3s",
        labels=dict(type__name="Class", class_instance_cnt="Count"),
    )
    class_refs_count_fig.update_layout(DEFAULT_LAYOUT)
    class_refs_count_fig.update_traces(
        textfont=dict(size=20),
        textposition="inside",
        showlegend=False,
    )

    return class_refs_count_fig
