from django.db.models import Q, Count, Max
import plotly.express as px
import numpy as np
import pandas as pd
from stats.models import Character, RefType, TextRef
from .config import DEFAULT_LAYOUT, DEFAULT_PLOTLY_THEME

characters = (
    Character.objects.all()
    .annotate(
        species_cnt=Count("species"),
        status_cnt=Count("status"),
    )
    .values()
)


def character_text_refs():
    # Character TextRef counts
    character_text_refs = (
        TextRef.objects.filter(Q(type__type=RefType.CHARACTER))
        .values("type__name")
        .annotate(char_instance_cnt=Count("type__name"))
    )

    if len(character_text_refs) == 0:
        return

    char_refs_count_fig = px.pie(
        character_text_refs,
        names="type__name",
        values="char_instance_cnt",
        template=DEFAULT_PLOTLY_THEME,
    )
    char_refs_count_fig.update_layout(DEFAULT_LAYOUT)
    char_refs_count_fig.update_traces(
        textposition="inside",
        customdata=np.stack(
            (character_text_refs.values_list("type__name", "char_instance_cnt"),),
            axis=-1,
        ),
        hovertemplate="<b>Character</b>: %{customdata[0][0]}<br>"
        + "<b>Reference Count</b>: %{customdata[0][1]}"
        + "<extra></extra>",
    )

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

    df = pd.DataFrame(char_counts_per_chapter, columns=["Chapter", "Character Count"])
    char_counts_per_chapter_fig = px.scatter(
        df,
        x="Chapter",
        y="Character Count",
        template=DEFAULT_PLOTLY_THEME,
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
    char_counts_per_chapter_fig.update_traces(
        hovertemplate="<b>Chapter</b>: %{x}<br>"
        + "<b>Total Characters</b>: %{y}"
        + "<extra></extra>"
    )
    return char_counts_per_chapter_fig


def characters_by_species():
    """Character counts by species"""
    # TODO: make this more robust and performant
    # currently scans Character.SPECIES choices tuple to match human-readable string
    for c in characters:
        c["species"] = Character.SPECIES[
            [x[0] for x in Character.SPECIES].index(c["species"])
        ][1]
        c["status"] = Character.STATUSES[
            [x[0] for x in Character.STATUSES].index(c["status"])
        ][1]
        # print(c)

    chars_by_species_fig = px.pie(
        characters,
        names="species",
        values="species_cnt",
        template=DEFAULT_PLOTLY_THEME,
    )
    chars_by_species_fig.update_layout(DEFAULT_LAYOUT)
    chars_by_species_fig.update_traces(
        textposition="inside",
        customdata=np.stack(
            (characters.values_list("species_cnt", "status_cnt"),), axis=-1
        ),
        hovertemplate="<b>Species</b>: %{label}<br>"
        + "<b>Characters</b>: %{value}"
        + "<extra></extra>",
    )

    return chars_by_species_fig


def characters_by_status():
    """Character counts by status"""
    chars_by_status_fig = px.pie(
        characters,
        names="status",
        values="status_cnt",
        template=DEFAULT_PLOTLY_THEME,
    )
    chars_by_status_fig.update_layout(DEFAULT_LAYOUT)
    chars_by_status_fig.update_traces(
        textposition="inside",
        customdata=np.stack((characters.values_list("status", "status_cnt"),), axis=-1),
        hovertemplate="<b>Status</b>: %{label}<br>"
        + "<b>Characters</b>: %{value}"
        + "<extra></extra>",
    )

    return chars_by_status_fig
