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


def word_count_charts():
    """Overview charts - all main word count charts to show on overview"""
    return {
        "plots": {
            "Word Counts by Chapter": word_count_per_chapter(),
            "Word Counts over Time": word_count_histogram(),
            "Word Counts by Book": word_count_by_book(),
            "Word Counts by Volume": word_count_by_volume(),
        },
        "page_title": "Word Counts",
    }


def character_charts():
    return {
        "plots": {
            "Character Reference Counts": character_text_refs(),
            "Unique Characters Per Chapter": character_counts_per_chapter(),
            "Character Species Counts": characters_by_species(),
            "Character Status Counts": characters_by_status(),
        },
        "page_title": "Character Stats",
    }


def class_charts():
    return {
        "plots": {
            "Class Reference Counts": class_ref_counts(),
        },
        "page_title": "Class Stats",
    }
