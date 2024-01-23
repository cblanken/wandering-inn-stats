from typing import Callable
from enum import Enum
from pathlib import Path
from plotly.graph_objects import Figure

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

    def save_thumbnail(self):
        fig = self.get_fig()
        with open(self.path, "wb") as f:
            f.write(fig.to_image(format="svg"))


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
