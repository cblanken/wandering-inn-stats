import numpy as np
import plotly.express as px
from django.db.models import Count, Max, Q
from django.db.models.manager import BaseManager
from plotly.graph_objects import Figure

from stats.models import Chapter, Character, RefType, TextRef

from .config import DEFAULT_DISCRETE_COLORS, DEFAULT_LAYOUT
from .gallery import ChartGalleryItem, Filetype
from .reftype_types import get_reftype_type_gallery


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


def get_character_charts(
    first_chapter: Chapter | None = None, last_chapter: Chapter | None = None
) -> list[ChartGalleryItem]:
    default_chart_gallery: list[ChartGalleryItem] = get_reftype_type_gallery(
        RefType.Type.CHARACTER, first_chapter, last_chapter
    )
    return default_chart_gallery + [
        # Custom gallery charts
        ChartGalleryItem(
            "Unique Characters per Chapter",
            "",
            Filetype.SVG,
            lambda: character_counts_per_chapter(first_chapter, last_chapter),
            popup_info="This chart counts how many different characters appear in each chapter. Note this one may take a moment to load the interactive chart due to all the calculations required.",
        ),
        ChartGalleryItem(
            "Character Species",
            "",
            Filetype.SVG,
            characters_by_species,
            popup_info="This chart shows the most common species for all the characters. Check out the interactive chart to see precise counts.",
            has_chapter_filter=False,
        ),
        ChartGalleryItem(
            "Character Statuses",
            "",
            Filetype.SVG,
            characters_by_status,
            popup_info='This chart shows the ratio of character statuses including: "Alive", "Deceased", "Undead" and "Unknown". Please note that while some characters\' statuses are specified as "Unknown" in the TWI Wiki, it is also the default for characters with a blank status or a status that is poorly formatted in the Wiki data.',
            has_chapter_filter=False,
        ),
    ]
