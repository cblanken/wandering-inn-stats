from enum import Enum
from pathlib import Path
from typing import Callable

from django.conf import settings
from django.utils.text import slugify
from plotly.graph_objects import Figure
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
    mentions as rt_mentions,
    cumulative_mentions as rt_cumulative_mentions,
    most_mentions_by_chapter as rt_most_mentions_by_chapter,
    most_mentions_by_book as rt_most_mentions_by_book,
    most_mentions_by_volume as rt_most_mentions_by_volume,
)

from .classes import class_ref_counts
from .skills import skill_ref_counts
from .magic import spell_ref_counts
from .locations import location_ref_counts
from stats.models import Chapter, RefType


pio.templates.default = "plotly_dark"


class Filetype(Enum):
    SVG = "svg"
    PNG = "png"
    JPG = "jpg"


def get_static_thumbnail_path(filename: str, filetype: Filetype, extra_path: Path = "") -> Path:
    return Path(
        "charts",
        filetype.value,
        extra_path,
        f"{filename}.{filetype.value}",
    )


def get_thumbnail_path(filename: str, filetype: Filetype, extra_path: Path = "") -> Path:
    return Path("stats", "static", get_static_thumbnail_path(filename, filetype, extra_path))


class ChartGalleryItem:
    def __init__(
        self,
        title: str,
        caption: str,
        filetype: Filetype,
        get_fig: Callable[[], Figure | None],
        subdir: Path = Path(),
        popup_info: str | None = None,
        has_chapter_filter: bool = True,
    ) -> None:
        self.title = title
        self.title_slug = slugify(title)
        self.caption = caption
        self.filetype = filetype
        self.static_path = get_static_thumbnail_path(self.title_slug, filetype, subdir)
        self.static_url = f"{settings.STATIC_URL}{self.static_path}"
        self.path = get_thumbnail_path(self.title_slug, filetype, subdir)
        self.get_fig: Callable[[], Figure | None] = get_fig
        self.popup_info: str | None = popup_info
        self.has_chapter_filter = has_chapter_filter


def get_reftype_gallery(
    rt: RefType,
    first_chapter: Chapter | None = None,
    last_chapter: Chapter | None = None,
) -> list[ChartGalleryItem]:
    return [
        ChartGalleryItem(
            "Total mentions",
            "",
            Filetype.SVG,
            lambda rt=rt: rt_cumulative_mentions(rt, first_chapter, last_chapter),
            subdir=Path(slugify(rt.type), rt.slug),
        ),
        ChartGalleryItem(
            "Mentions",
            "",
            Filetype.SVG,
            lambda rt=rt: rt_mentions(rt, first_chapter, last_chapter),
            subdir=Path(slugify(rt.type), rt.slug),
        ),
        ChartGalleryItem(
            "Chapters with the most mentions",
            "",
            Filetype.SVG,
            lambda rt=rt: rt_most_mentions_by_chapter(rt, first_chapter, last_chapter),
            subdir=Path(slugify(rt.type), rt.slug),
            popup_info='Interlude chapters are abbreviated with "I." for readability.',
        ),
        ChartGalleryItem(
            "Books with the most mentions",
            "",
            Filetype.SVG,
            lambda rt=rt: rt_most_mentions_by_book(rt, first_chapter, last_chapter),
            subdir=Path(slugify(rt.type), rt.slug),
            popup_info="These counts only include released books, so, if mentions occur outside that range, they won't appear in this chart.",
        ),
        ChartGalleryItem(
            "Volumes with the most mentions",
            "",
            Filetype.SVG,
            lambda rt=rt: rt_most_mentions_by_volume(rt, first_chapter, last_chapter),
            subdir=Path(slugify(rt.type), rt.slug),
        ),
    ]


def get_word_count_charts(
    first_chapter: Chapter | None = None,
    last_chapter: Chapter | None = None,
) -> list[ChartGalleryItem]:
    return [
        ChartGalleryItem(
            "Word Counts by Chapter",
            "",
            Filetype.SVG,
            lambda: word_count_per_chapter(first_chapter, last_chapter),
        ),
        ChartGalleryItem(
            "Total Word Counts over Time",
            "",
            Filetype.SVG,
            lambda: word_count_cumulative(first_chapter, last_chapter),
        ),
        ChartGalleryItem(
            "Word Counts by Book",
            "",
            Filetype.SVG,
            lambda: word_count_by_book(first_chapter, last_chapter),
            popup_info="Volumes often span multiple books. The bars in this chart are colored to indicate books belonging to the same volume.",
        ),
        ChartGalleryItem(
            "Word Counts by Volume",
            "",
            Filetype.SVG,
            lambda: word_count_by_volume(first_chapter, last_chapter),
            popup_info="Volumes often span multiple books. Each volume bar is sectioned by color to indicate different books.",
        ),
    ]


def get_character_charts(
    first_chapter: Chapter | None = None,
    last_chapter: Chapter | None = None,
) -> list[ChartGalleryItem]:
    return [
        ChartGalleryItem(
            "Character Mentions",
            "",
            Filetype.SVG,
            lambda: character_text_refs(first_chapter, last_chapter),
            popup_info="This chart lists the most mentioned characters. Each character's mention count is the total number of times a character has been mentioned by name or by one of their aliases. To see more details, check out the character specific pages linked in the table below.",
        ),
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


def get_class_charts(
    first_chapter: Chapter | None = None,
    last_chapter: Chapter | None = None,
) -> list[ChartGalleryItem]:
    return [
        ChartGalleryItem(
            "Class Mentions",
            "",
            Filetype.SVG,
            lambda: class_ref_counts(first_chapter, last_chapter),
        ),
    ]


def get_skill_charts(
    first_chapter: Chapter | None = None,
    last_chapter: Chapter | None = None,
) -> list[ChartGalleryItem]:
    return [
        ChartGalleryItem(
            "Skill Mentions",
            "",
            Filetype.SVG,
            lambda: skill_ref_counts(first_chapter, last_chapter),
        ),
    ]


def get_magic_charts(
    first_chapter: Chapter | None = None,
    last_chapter: Chapter | None = None,
) -> list[ChartGalleryItem]:
    return [
        ChartGalleryItem(
            "Spell Mentions",
            "",
            Filetype.SVG,
            lambda: spell_ref_counts(first_chapter, last_chapter),
        ),
    ]


def get_location_charts(
    first_chapter: Chapter | None = None,
    last_chapter: Chapter | None = None,
) -> list[ChartGalleryItem]:
    return [
        ChartGalleryItem(
            "Location Mentions",
            "",
            Filetype.SVG,
            lambda: location_ref_counts(first_chapter, last_chapter),
        ),
    ]
