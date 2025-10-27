from stats.models import Chapter

from .gallery import ChartGalleryItem, Filetype
from .word_counts import (
    word_count_by_book,
    word_count_by_volume,
    word_count_cumulative,
    word_count_per_chapter,
)


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
