from django.db.models import Count, F, Q, Sum, Value, Case
import plotly.express as px
import numpy as np
import pandas as pd
from .models import Chapter, RefType, TextRef, Character

px.defaults.height = 800

def word_count_charts():
    """Word count charts"""
    # Word counts per chapter
    chapter_wc_data = (Chapter.objects
        .values("title", "word_count")
        .order_by("id")
    )

    chapter_wc_fig = px.scatter(chapter_wc_data, title="Word Count Per Chapter",
        x="title", y="word_count"
    )

    chapter_wc_html = chapter_wc_fig.to_html(full_html=False, include_plotlyjs=False)


    # Word counts per author's note
    chapter_wc_data = (Chapter.objects
        .filter(authors_note_word_count__gt=0)
        .values("title", "authors_note_word_count")
        .order_by("id")
    )

    chapter_authors_wc_fig = px.line(chapter_wc_data, title="Word Count Per Author's Note",
        x="title", y="authors_note_word_count"
    )

    chapter_authors_wc_html = chapter_authors_wc_fig.to_html(full_html=False, include_plotlyjs=False)


    # Word counts grouped by book
    book_wc_data = (Chapter.objects
        .filter(~Q(book__title__contains="Unreleased"))
        .values("book", "book__title", "id", "title", "word_count")
        .order_by("book", "number")
    )

    book_wc_fig = px.bar(book_wc_data, title="Word Count Per Book",
        x="book__title", y="word_count", color="book",
        color_continuous_scale=px.colors.qualitative.Vivid)
    book_wc_fig.update_layout(
        xaxis={"title": "Book"},
        yaxis={"title": "Word Count"},
        showlegend=False,
        coloraxis_showscale=False
    )

    book_wc_fig.update_traces(
        customdata = np.stack((
            book_wc_data.values_list("title"),
        ), axis=-1),
        hovertemplate=
            "<b>Book</b>: %{x}<br>" +
            "<b>Chapter</b>: %{customdata[0]}<br>" +
            "<b>Word Count</b>: %{y}" +
            "<extra></extra>"
    )


    book_wc_html = book_wc_fig.to_html(full_html=False, include_plotlyjs=False)

    # Word counts grouped by volume
    volume_wc_data = (Chapter.objects
        .values("book__volume", "book__volume__title", "id", "title", "word_count")
        .order_by("book__volume", "number")
    )

    volume_wc_fig = px.bar(volume_wc_data, title="Word Count Per Volume",
        x="book__volume__title", y="word_count", color="book__volume",
        color_continuous_scale=px.colors.qualitative.Vivid)
    volume_wc_fig.update_layout(
        xaxis={"title": "Volume"},
        yaxis={"title": "Word Count"},
        showlegend=False,
        coloraxis_showscale=False
    )
    volume_wc_fig.update_traces(
        customdata = np.stack((
            volume_wc_data.values_list("title"),
        ), axis=-1),
        hovertemplate=
            "<b>volume</b>: %{x}<br>" +
            "<b>Chapter</b>: %{customdata[0]}<br>" +
            "<b>Word Count</b>: %{y}" +
            "<extra></extra>"
    )

    volume_wc_html = volume_wc_fig.to_html(full_html=False, include_plotlyjs=False)


    return {
        "plots": {
            "Word Counts by Chapter": chapter_wc_html,
            "Word Counts by Author's Note": chapter_authors_wc_html,
            "Word Counts by Book": book_wc_html,
            "Word Counts by Volume": volume_wc_html,
        },
        "page_title": "Word Counts"
    }

def character_charts():
    """Character stat charts"""

    # Character TextRef counts
    character_text_refs = (TextRef.objects
        .filter(Q(type__type=RefType.CHARACTER))
        .values("type__name")
        .annotate(char_instance_cnt=Count("type__name"))
    )

    char_refs_count_fig = px.pie(character_text_refs, names="type__name", values="char_instance_cnt",
           title="Character TextRef Counts")
    char_refs_count_fig.update_traces(textposition="inside")
    char_refs_count_html = char_refs_count_fig.to_html(full_html=False, include_plotlyjs=False)

    char_counts_per_chapter = [(Character.objects
        .filter(first_chapter_ref__number__lt=i)
        .aggregate(chapter_cnt_per=Count("ref_type"))["chapter_cnt_per"]
    ) for i in ([x.number for x in Chapter.objects.all()])]

    char_counts_per_chapter = [x for x in zip(range(len(char_counts_per_chapter)), char_counts_per_chapter)]
    
    df = pd.DataFrame(char_counts_per_chapter, columns=["Chapter", "Character Count"])
    char_counts_per_chapter_fig = px.line(df, x="Chapter", y="Character Count")
    char_counts_per_chapter_html = char_counts_per_chapter_fig.to_html(full_html=False, include_plotlyjs=False)


    # Character data counts
    characters = (Character.objects.all()
        .annotate(species_cnt=Count("species"), status_cnt=Count("status"))
        .values()
    )

    # Character counts by species
    chars_by_species_fig = px.pie(characters, names="species", values="species_cnt",
           title="Characters by Species")
    chars_by_species_fig.update_traces(textposition="inside")
    chars_by_species_html = chars_by_species_fig.to_html(full_html=False, include_plotlyjs=False)

    # Character counts by status
    chars_by_status_fig = px.pie(characters, names="status", values="status_cnt",
           title="Characters by Status")
    chars_by_status_fig.update_traces(textposition="inside")
    chars_by_status_html = chars_by_status_fig.to_html(full_html=False, include_plotlyjs=False)

    return {
        "plots": {
            "Character Reference Counts": char_refs_count_html,
            "Character Species Counts": chars_by_species_html,
            "Character Status Counts": chars_by_status_html,
            "Character Counts Per Chapter": char_counts_per_chapter_html
         },
        "page_title": "Character Stats"
    }


# Class counts per chapter/book/volume with subplots
def class_charts():
    class_refs = (TextRef.objects
        .filter(type__type=RefType.CLASS)
        .values("type__name")
        .annotate(class_instance_cnt=Count("type__name"))
    )

    class_refs_count_fig = px.pie(class_refs, names="type__name", values="class_instance_cnt",
        title="Class TextRefCounts")
    
    class_refs_count_fig.update_traces(textposition="inside")

    class_refs_count_html = class_refs_count_fig.to_html(full_html=False, include_plotlyjs=False)

    return {
        "plots": {
            "Class Reference Counts": class_refs_count_html,
        },
        "page_title": "Class Stats"
    }


# Skill counts per chapter/book/volume with subplots
# Spellcounts per chapter/book/volume with subplots
# Locations counts per chapter/book/volume with subplots
# Item counts per chapter/book/volume with subplots

# isDivine toggle for Classes/Skills/Spells