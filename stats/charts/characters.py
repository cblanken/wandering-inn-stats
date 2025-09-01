from django.db.models import Q, Count, Max
from django.db.models.manager import BaseManager
import plotly.express as px
from plotly.graph_objects import Figure
import numpy as np
from stats.models import Character, RefType, TextRef, Chapter
from .config import DEFAULT_LAYOUT, DEFAULT_DISCRETE_COLORS


def character_text_refs(first_chapter: Chapter | None = None, last_chapter: Chapter | None = None) -> Figure | None:
    character_text_refs = TextRef.objects.filter(Q(type__type=RefType.CHARACTER))

    if first_chapter:
        character_text_refs = character_text_refs.filter(chapter_line__chapter__number__gte=first_chapter.number)

    if last_chapter:
        character_text_refs = character_text_refs.filter(chapter_line__chapter__number__lte=last_chapter.number)

    character_text_refs = (
        character_text_refs.values("type__name")
        .annotate(char_instance_cnt=Count("type__name"))
        .order_by("-char_instance_cnt")
    )

    if len(character_text_refs) == 0:
        return None

    char_refs_count_fig = px.bar(
        character_text_refs[:15],
        x="char_instance_cnt",
        y="type__name",
        color="type__name",
        color_discrete_sequence=DEFAULT_DISCRETE_COLORS,
        text_auto="d",
        labels={"type__name": "Name", "char_instance_cnt": "Mentions"},
    )

    char_refs_count_fig.update_layout(DEFAULT_LAYOUT)
    char_refs_count_fig.update_traces(showlegend=False)

    return char_refs_count_fig


def character_counts_per_chapter(first_chapter: Chapter | None = None, last_chapter: Chapter | None = None) -> Figure:
    def get_text_refs(num: int) -> BaseManager[TextRef]:
        tr = TextRef.objects.filter(Q(chapter_line__chapter__number=num) & Q(type__type="CH"))
        if first_chapter:
            tr = tr.filter(chapter_line__chapter__number__gte=first_chapter.number)

        if last_chapter:
            tr = tr.filter(chapter_line__chapter__number__lte=last_chapter.number)

        return tr

    if first_chapter:
        min_chapter: int = first_chapter.number
    else:
        min_chapter: int = 0

    if last_chapter:
        max_chapter: int = last_chapter.number
    else:
        max_chapter: int = TextRef.objects.values().aggregate(max=Max("chapter_line__chapter__number"))["max"]

    char_counts_per_chapter = [
        (
            num,
            get_text_refs(num).values("type__name").annotate(cnt=Count("type__name")).count(),
        )
        for num in range(min_chapter, max_chapter)
    ]

    char_counts_per_chapter_fig = px.scatter(
        char_counts_per_chapter,
        x=0,
        y=1,
        trendline="lowess",
        trendline_options={"frac": 0.2},
        trendline_color_override="#FF8585",
    )
    char_counts_per_chapter_fig.update_layout(
        DEFAULT_LAYOUT,
        xaxis={
            "title": "Chapter Number",
            "rangeslider": {"visible": True},
            "type": "linear",
        },
        yaxis={"title": "Character Count"},
    )

    char_counts_per_chapter_fig.data[0]["hovertemplate"] = (
        "<b>Chapter Number</b>: %{x}<br>" + "<b>Total Characters</b>: %{y}<br>" + "<extra></extra>"
    )
    return char_counts_per_chapter_fig


def characters_by_species() -> Figure:
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
        c["species"] = Character.SPECIES[[x[0] for x in Character.SPECIES].index(c["species"])][1]

    chars_by_species_fig = px.bar(
        characters,
        x="species_cnt",
        y="species",
        color="species",
        color_discrete_sequence=DEFAULT_DISCRETE_COLORS,
        labels={"species": "Species", "species_cnt": "Count"},
    )
    chars_by_species_fig.update_layout(DEFAULT_LAYOUT)
    chars_by_species_fig.update_traces(
        textposition="inside",
        showlegend=False,
    )

    return chars_by_species_fig


def characters_by_status() -> Figure:
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
        c["status"] = Character.STATUSES[[x[0] for x in Character.STATUSES].index(c["status"])][1]

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
        hovertemplate="<b>Status</b>: %{label}<br>" + "<b>Characters</b>: %{value}" + "<extra></extra>",
    )

    return chars_by_status_fig
