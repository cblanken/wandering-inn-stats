from enum import Enum
from pathlib import Path
from typing import Callable
from urllib.parse import quote

from django.conf import settings
from django.db.models import Count
from django.utils.text import slugify
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

from .reftypes import (
    histogram as rt_histogram,
    histogram_cumulative as rt_histogram_cumulative,
    most_mentions_by_chapter as rt_most_mentions,
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


def get_static_thumbnail_path(
    filename: str, filetype: Filetype, extra_path: Path = ""
) -> Path:
    return Path(
        "charts",
        filetype.value,
        extra_path,
        f"{filename}.{filetype.value}",
    )


def get_thumbnail_path(
    filename: str, filetype: Filetype, extra_path: Path = ""
) -> Path:
    return Path("stats", get_static_thumbnail_path(filename, filetype, extra_path))


def save_thumbnail(fig: Figure, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(fig.to_image(format="svg"))


class ChartGalleryItem:
    def __init__(
        self,
        title: str,
        caption: str,
        filetype: Filetype,
        get_fig: Callable[[], Figure],
        subdir: Path = "",
    ):
        self.title = title
        self.title_slug = slugify(title)
        self.caption = caption
        self.filetype = filetype
        self.static_path = get_static_thumbnail_path(self.title_slug, filetype, subdir)
        self.static_url = f"{settings.STATIC_URL}{self.static_path}"
        self.path = get_thumbnail_path(self.title_slug, filetype, subdir)
        self.get_fig: Callable[[], Figure] = get_fig


def get_reftype_gallery(rt: RefType) -> list[ChartGalleryItem]:
    return [
        ChartGalleryItem(
            "Total mentions",
            "",
            Filetype.SVG,
            lambda rt=rt: rt_histogram(rt),
            subdir=Path(slugify(rt.type), rt.slug),
        ),
        ChartGalleryItem(
            "Mentions",
            "",
            Filetype.SVG,
            lambda rt=rt: rt_histogram_cumulative(rt),
            subdir=Path(slugify(rt.type), rt.slug),
        ),
        ChartGalleryItem(
            "Most mentioned chapters",
            "",
            Filetype.SVG,
            lambda rt=rt: rt_most_mentions(rt),
            subdir=Path(slugify(rt.type), rt.slug),
        ),
    ]


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
    ChartGalleryItem("Character Mentions", "", Filetype.SVG, character_text_refs),
    ChartGalleryItem(
        "Unique Characters per Chapter", "", Filetype.SVG, character_counts_per_chapter
    ),
    ChartGalleryItem("Character Species", "", Filetype.SVG, characters_by_species),
    ChartGalleryItem("Character Statuses", "", Filetype.SVG, characters_by_status),
]


class_charts: list[ChartGalleryItem] = [
    ChartGalleryItem("Class Mentions", "", Filetype.SVG, class_ref_counts)
]

skill_charts: list[ChartGalleryItem] = [
    ChartGalleryItem("Skill Mentions", "", Filetype.SVG, skill_ref_counts),
]

magic_charts: list[ChartGalleryItem] = [
    ChartGalleryItem("Spell Mentions", "", Filetype.SVG, spell_ref_counts),
]
