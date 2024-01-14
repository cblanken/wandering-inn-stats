from django.db.models import Count
import plotly.express as px
import numpy as np
from stats.models import RefType, TextRef
from .config import DEFAULT_LAYOUT, DEFAULT_PLOTLY_THEME


def class_ref_counts():
    class_refs = (
        TextRef.objects.filter(type__type=RefType.CLASS)
        .values("type__name")
        .annotate(class_instance_cnt=Count("type__name"))
    )

    if len(class_refs) == 0:
        return

    class_refs_count_fig = px.pie(
        class_refs,
        names="type__name",
        values="class_instance_cnt",
        template=DEFAULT_PLOTLY_THEME,
    )

    class_refs_count_fig.update_layout(DEFAULT_LAYOUT)
    class_refs_count_fig.update_traces(textposition="inside")
    class_refs_count_fig.update_traces(
        textposition="inside",
        customdata=np.stack(
            (class_refs.values_list("type__name", "class_instance_cnt"),),
            axis=-1,
        ),
        hovertemplate="<b>Class</b>: %{customdata[0][0]}<br>"
        + "<b>Reference Count</b>: %{customdata[0][1]}"
        + "<extra></extra>",
    )

    return class_refs_count_fig.to_html(
        full_html=False,
        include_plotlyjs=False,
    )
