from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Sum
import plotly.express as px
import pandas as pd
from .models import Chapter, Book

def index(request):
    return HttpResponse("Stats.")

def charts(request):

    charts = []


    # Word counts grouped by chapter/book/volume with subplots


    # Character counts per chapter/book/volume with subplots
    # Skill counts per chapter/book/volume with subplots
    # Class counts per chapter/book/volume with subplots
    # Spellcounts per chapter/book/volume with subplots
    # Locations counts per chapter/book/volume with subplots
    # Item counts per chapter/book/volume with subplots

    # isDivine toggle for Classes/Skills/Spells


    #chapter_df = pd.DataFrame(Chapter.objects.filter().values())
    chapter_df = pd.DataFrame(Chapter.objects.values())

    fig_bar = px.bar(chapter_df.groupby("book_id"), x="book_id", y="word_count", title="Word Count Per Book")
    bar_chart = fig_bar.to_html(full_html=False, include_plotlyjs=False)

    return render(request, "plotly.html", {"bar_chart": bar_chart })
