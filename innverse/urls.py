from django.contrib import admin
from django.apps import apps
from django.urls import path, include

from . import views

urlpatterns = [
    path("overview", views.overview, name="overview"),
    path("characters", views.characters, name="characters"),
    path("classes", views.classes),
    path("skills", views.skills),
    path("magic", views.magic),
    path("search", views.search),
    path("about", views.about),
    path("settings", views.settings),
    path("stats/", include("stats.urls")),
    path("admin/", admin.site.urls),
    path("__debug__/", include("debug_toolbar.urls")),
    path("__reload__", include("django_browser_reload.urls")),
]

if apps.is_installed("pattern_library"):
    urlpatterns += [
        path("pattern-library/", include("pattern_library.urls")),
    ]
