from django.shortcuts import render
from django.http import HttpResponse

def overview(request):
    return render(request, "pages/overview.html")

def characters(request):
    return render(request, "pages/characters.html")

def classes(request):
    return render(request, "pages/classes.html")

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