from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.cache import cache_page
from stats.charts import word_count_charts, character_charts, class_charts
from stats.models import RefType, TextRef
from .forms import SearchForm


@cache_page(60)
def overview(request):
    return render(request, "pages/overview.html", word_count_charts())


@cache_page(60)
def characters(request):
    return render(request, "pages/characters.html", character_charts())


@cache_page(60)
def classes(request):
    return render(request, "pages/classes.html", class_charts())


@cache_page(60)
def skills(request):
    return render(request, "pages/skills.html")


@cache_page(60)
def magic(request):
    return render(request, "pages/magic.html")


def search(request):
    if request.method == "GET":
        form = SearchForm(request.GET)
        print("DATA", form.data)

        if form.is_valid():
            context = {
                "type": form.cleaned_data.get("type"),
                "query": form.cleaned_data.get("query"),
            }

            # Query TextRefs per form parameters
            table_data = TextRef.objects.filter(
                Q(type__type=context.get("type"))
                & Q(chapter_line__text__contains=context.get("query"))
            )

            context["table_data"] = table_data
            return render(request, "pages/search.html", context)
        else:
            # Form data not valid
            return render(request, "pages/search.html")
    else:
        return render(request, "pages/search.html")


@cache_page(60 * 60 * 24)
def about(request):
    return render(request, "pages/about.html")


def settings(request):
    return render(request, "pages/settings.html")
