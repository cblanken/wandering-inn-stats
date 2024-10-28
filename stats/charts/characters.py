from django.db.models import Q, Count, Max
import plotly.express as px
import numpy as np
from stats.models import Character, RefType, TextRef
from .config import DEFAULT_LAYOUT, DEFAULT_DISCRETE_COLORS


def character_text_refs():
    character_text_refs = (
        TextRef.objects.filter(Q(type__type=RefType.CHARACTER))
        .values("type__name")
        .annotate(char_instance_cnt=Count("type__name"))
        .order_by("-char_instance_cnt")
    )

    if len(character_text_refs) == 0:
        return

    char_refs_count_fig = px.bar(
        character_text_refs[:15],
        x="char_instance_cnt",
        y="type__name",
        color="type__name",
        color_discrete_sequence=DEFAULT_DISCRETE_COLORS,
        text_auto=".3s",
        labels={"type__name": "Name", "char_instance_cnt": "Mentions"},
    )

    char_refs_count_fig.update_layout(DEFAULT_LAYOUT)
    char_refs_count_fig.update_traces(showlegend=False)

    return char_refs_count_fig


def character_counts_per_chapter():
    char_counts_per_chapter = [
        (
            num,
            TextRef.objects.filter(
                Q(chapter_line__chapter__number=num) & Q(type__type="CH")
            )
            .values("type__name")
            .annotate(cnt=Count("type__name"))
            .count(),
        )
        for num in range(
            TextRef.objects.values().aggregate(
                max=Max("chapter_line__chapter__number")
            )["max"]
        )
    ]

    char_counts_per_chapter_fig = px.scatter(
        char_counts_per_chapter,
        x=0,
        y=1,
        trendline="lowess",
        trendline_options=dict(frac=0.2),
        trendline_color_override="#FF8585",
    )
    char_counts_per_chapter_fig.update_layout(
        DEFAULT_LAYOUT,
        xaxis=dict(
            title="Chapter Number",
            rangeslider=dict(visible=True),
            type="linear",
        ),
        yaxis=dict(title="Character Count"),
    )

    char_counts_per_chapter_fig.data[0]["hovertemplate"] = (
        "<b>Chapter</b>: %{x}<br>" + "<b>Total Characters</b>: %{y}" + "<extra></extra>"
    )
    return char_counts_per_chapter_fig


def characters_by_species():
    characters = (
        Character.objects.all()
        .values("species")
        .annotate(
            species_cnt=Count("species"),
        )
        .order_by("-species_cnt")[:15]
    )

    """Character counts by species"""
    # TODO: make this more robust and performant
    # currently scans Character.SPECIES choices tuple to match human-readable string
    for c in characters:
        c["species"] = Character.SPECIES[
            [x[0] for x in Character.SPECIES].index(c["species"])
        ][1]

    chars_by_species_fig = px.bar(
        characters,
        x="species_cnt",
        y="species",
        color="species",
        color_discrete_sequence=DEFAULT_DISCRETE_COLORS,
        labels=dict(species="Species", species_cnt="Count"),
    )
    chars_by_species_fig.update_layout(DEFAULT_LAYOUT)
    chars_by_species_fig.update_traces(
        textposition="inside",
        showlegend=False,
    )

    return chars_by_species_fig


def characters_by_status():
    """Character counts by status"""
    characters = (
        Character.objects.all()
        .values("status")
        .annotate(
            status_cnt=Count("status"),
        )
        .order_by("-status_cnt")
    )

    for c in characters:
        c["status"] = Character.STATUSES[
            [x[0] for x in Character.STATUSES].index(c["status"])
        ][1]

    chars_by_status_fig = px.pie(
        characters,
        names="status",
        values="status_cnt",
    )
    chars_by_status_fig.update_layout(DEFAULT_LAYOUT)
    chars_by_status_fig.update_traces(
        textposition="auto",
        textinfo="label+percent",
        customdata=np.stack((characters.values_list("status", "status_cnt"),), axis=-1),
        hovertemplate="<b>Status</b>: %{label}<br>"
        + "<b>Characters</b>: %{value}"
        + "<extra></extra>",
    )

    return chars_by_status_fig
