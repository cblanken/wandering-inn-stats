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
    word_count_cumulative,
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
from .locations import location_ref_counts
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
    return Path(
        "stats", "static", get_static_thumbnail_path(filename, filetype, extra_path)
    )


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
        subdir: Path = Path(),
        popup_info: str | None = None,
    ):
        self.title = title
        self.title_slug = slugify(title)
        self.caption = caption
        self.filetype = filetype
        self.static_path = get_static_thumbnail_path(self.title_slug, filetype, subdir)
        self.static_url = f"{settings.STATIC_URL}{self.static_path}"
        self.path = get_thumbnail_path(self.title_slug, filetype, subdir)
        self.get_fig: Callable[[], Figure] = get_fig
        self.popup_info: str | None = popup_info


def get_reftype_gallery(rt: RefType) -> list[ChartGalleryItem]:
    return [
        ChartGalleryItem(
            "Total mentions",
            "",
            Filetype.SVG,
            lambda rt=rt: rt_histogram_cumulative(rt),
            subdir=Path(slugify(rt.type), rt.slug),
        ),
        ChartGalleryItem(
            "Mentions",
            "",
            Filetype.SVG,
            lambda rt=rt: rt_histogram(rt),
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
        "Total Word Counts over Time", "", Filetype.SVG, word_count_cumulative
    ),
    ChartGalleryItem(
        "Word Counts by Book",
        "",
        Filetype.SVG,
        word_count_by_book,
        popup_info="Volumes often span multiple books. The bars in this chart are colored to indicate books belonging to the same volume.",
    ),
    ChartGalleryItem(
        "Word Counts by Volume",
        "",
        Filetype.SVG,
        word_count_by_volume,
        popup_info="Volumes often span multiple books. Each volume bar is sectioned by color to indicate different books.",
    ),
]


character_charts: list[ChartGalleryItem] = [
    ChartGalleryItem(
        "Character Mentions",
        "",
        Filetype.SVG,
        character_text_refs,
        popup_info="This chart lists the most mentioned characters. Each character's mention count is the total number of times a character has been mentioned by name or by one of their aliases. To see more details, check out the character specific pages linked in the table below.",
    ),
    ChartGalleryItem(
        "Unique Characters per Chapter",
        "",
        Filetype.SVG,
        character_counts_per_chapter,
        popup_info="This chart counts how many different characters appear in each chapter. Note this one may take a moment to load the interactive chart due to all the calculations required.",
    ),
    ChartGalleryItem(
        "Character Species",
        "",
        Filetype.SVG,
        characters_by_species,
        popup_info="This chart shows the most common species for all the characters. Check out the interactive chart to see precise counts.",
    ),
    ChartGalleryItem(
        "Character Statuses",
        "",
        Filetype.SVG,
        characters_by_status,
        popup_info='This chart shows the ratio of character statuses including: "Alive", "Deceased", "Undead" and "Unknown". Please note that while some characters\' statuses are specified as "Unknown" in the TWI Wiki, it is also the default for characters with a blank status or a status that is poorly formatted in the Wiki data. Each character\'s status can be found in the table below.',
    ),
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

location_charts: list[ChartGalleryItem] = [
    ChartGalleryItem("Location Mentions", "", Filetype.SVG, location_ref_counts),
]
