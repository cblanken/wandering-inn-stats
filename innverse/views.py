from django.shortcuts import render
from django.http import HttpResponse
from stats.charts import word_count_charts, character_charts, class_charts

def overview(request):
    return render(request, "pages/overview.html", word_count_charts())

def characters(request):
    return render(request, "pages/characters.html", character_charts())

def classes(request):
    return render(request, "pages/classes.html", class_charts())

def skills(request):
    return render(request, "pages/skills.html")

def magic(request):
    return render(request, "pages/magic.html")

def search(request):
    return render(request, "pages/search.html")

def about(request):
    return render(request, "pages/about.html")

def settings(request):
    return render(request, "pages/settings.html")