from django.shortcuts import render
from django.db.models import Count, F, Q, Sum, Value
import plotly.express as px
import numpy as np
import pandas as pd
from ..models import Chapter, RefType, TextRef

def index(request):
    return render(request, "chart_index.html", {
        "links": {
            "Word Counts": "./charts/word_counts",
            "Character Stats": "./charts/characters"
        }
    })

def word_count_charts(request):
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


    # Word counts grouped by book
    book_wc_data = (Chapter.objects
        .filter(~Q(book__title__contains="Unreleased"))
        .values("book", "book__title", "id", "title", "word_count")
        .order_by("book")
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
        .order_by("book__volume")
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




    return render(request, "chart_demo.html", {
        "plots": {
            "Word Counts by Chapter": chapter_wc_html,
            "Word Counts by Book": book_wc_html,
            "Word Counts by Volume": volume_wc_html,
        },
        "page_title": "Word Counts"
    })

def character_charts(request):
    """Character stat charts"""

    character_refs = (TextRef.objects
        .filter(Q(type__type=RefType.CHARACTER))
        .values("type__name")
        .annotate(char_instance_cnt=Count("type__name"))
    )

    char_refs_count_fig = px.pie(character_refs, names="type__name", values="char_instance_cnt",
           title="Character TextRef Counts")

    char_refs_count_fig.update_traces(textposition="inside")
    
    char_refs_count_html = char_refs_count_fig.to_html(full_html=False, include_plotlyjs=False)

    return render(request, "chart_demo.html", {
        "plots": {
            "Character Reference Counts": char_refs_count_html,
         },
        "page_title": "Character Stats"
    })


# Skill counts per chapter/book/volume with subplots
# Class counts per chapter/book/volume with subplots
# Spellcounts per chapter/book/volume with subplots
# Locations counts per chapter/book/volume with subplots
# Item counts per chapter/book/volume with subplots

# isDivine toggle for Classes/Skills/Spells