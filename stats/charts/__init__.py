from enum import Enum
from pathlib import Path
from typing import Callable

from django.db.models import Count
from plotly.graph_objects import Figure
import plotly.express as px
import plotly.io as pio

from .word_counts import (
    word_count_per_chapter,
    word_count_histogram,
    word_count_by_book,
    word_count_by_volume,
)

from .characters import (
    character_text_refs,
    character_counts_per_chapter,
    characters_by_species,
    characters_by_status,
)

from .classes import class_ref_counts
from .skills import skill_ref_counts
from .magic import spell_ref_counts
from stats.models import RefType, TextRef


pio.templates.default = "plotly_dark"


class Filetype(Enum):
    SVG = "svg"
    PNG = "png"
    JPG = "jpg"


def get_static_thumbnail_path(filename: str, filetype: Filetype) -> Path:
    return Path(
        f"static/charts/{filetype.value}",
        f"{filename}.{filetype.value}",
    )


def get_thumbnail_path(filename: str, filetype: Filetype) -> Path:
    return Path("stats", get_static_thumbnail_path(filename, filetype))


def save_thumbnail(fig: Figure, path: Path):
    with open(path, "wb") as f:
        f.write(fig.to_image(format="svg"))


class ChartGalleryItem:
    def __init__(
        self,
        title: str,
        caption: str,
        filetype: Filetype,
        get_fig: Callable[[], Figure],
    ):
        self.title = title
        self.title_slug = title.strip().lower().replace(" ", "_")
        self.caption = caption
        self.filetype = filetype
        self.static_path = get_static_thumbnail_path(self.title_slug, filetype)
        self.path = get_thumbnail_path(self.title_slug, filetype)
        self.get_fig: Callable[[], Figure] = get_fig


def get_reftype_mention_history(rt: RefType):
    chapter_counts = (
        TextRef.objects.filter(type=rt)
        .order_by("chapter_line__chapter__post_date")
        .values("chapter_line__chapter__title", "chapter_line__chapter")
        .annotate(count=Count("chapter_line__chapter"))
    )
    histo1 = px.histogram(
        chapter_counts,
        title=rt.name,
        x="chapter_line__chapter__title",
        y="count",
        labels={"chapter_line__chapter__title": "title", "count": "mentions"},
        template="plotly_dark",
        cumulative=True,
    )
    histo2 = px.histogram(
        chapter_counts,
        title=rt.name,
        x="chapter_line__chapter__title",
        y="count",
        labels={"chapter_line__chapter__title": "title", "count": "mentions"},
        template="plotly_dark",
    )
    top20_chapters = px.bar(
        chapter_counts.order_by("-count")[:20],
        title=rt.name,
        x="chapter_line__chapter__title",
        y="count",
        labels={"count": "mentions", "chapter_line__chapter__title": "title"},
        template="plotly_dark",
    )

    return (histo1, histo2, top20_chapters)


word_count_charts: list[ChartGalleryItem] = [
    ChartGalleryItem(
        "Word Counts by Chapter", "", Filetype.SVG, word_count_per_chapter
    ),
    ChartGalleryItem(
        "Total Word Counts over Time", "", Filetype.SVG, word_count_histogram
    ),
    ChartGalleryItem("Word Counts by Book", "", Filetype.SVG, word_count_by_book),
    ChartGalleryItem("Word Counts by Volume", "", Filetype.SVG, word_count_by_volume),
]


character_charts: list[ChartGalleryItem] = [
    ChartGalleryItem("Character References", "", Filetype.SVG, character_text_refs),
    ChartGalleryItem(
        "Unique Characters per Chapter", "", Filetype.SVG, character_counts_per_chapter
    ),
    ChartGalleryItem("Character Species", "", Filetype.SVG, characters_by_species),
    ChartGalleryItem("Character Statuses", "", Filetype.SVG, characters_by_status),
]


class_charts: list[ChartGalleryItem] = [
    ChartGalleryItem("Class References", "", Filetype.SVG, class_ref_counts)
]

skill_charts: list[ChartGalleryItem] = [
    ChartGalleryItem("Skill References", "", Filetype.SVG, skill_ref_counts),
]

magic_charts: list[ChartGalleryItem] = [
    ChartGalleryItem("Spell References", "", Filetype.SVG, spell_ref_counts),
]
