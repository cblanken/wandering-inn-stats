from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.cache import cache_page
from stats.charts import word_count_charts, character_charts, class_charts


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
        print(request.GET)
        context = {
            "type": request.GET.get("type"),
            "query": request.GET.get("query", ""),
        }
        return render(request, "pages/search.html", context)
    else:
        return render(request, "pages/search.html")


@cache_page(60 * 60 * 24)
def about(request):
    return render(request, "pages/about.html")


def settings(request):
    return render(request, "pages/settings.html")
