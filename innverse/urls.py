from django.contrib import admin
from django.apps import apps
from django.http import HttpResponseRedirect
from django.urls import path, include, reverse
from . import views


def overview_redirect(req):
    return HttpResponseRedirect(reverse(views.overview))


app_name = "innverse"
urlpatterns = [
    # Main page
    path("", overview_redirect),
    path("overview/", views.overview, name="overview"),
    path("overview/charts/<slug:chart>", views.main_interactive_chart),
    # Characters
    path("characters/", views.characters, name="character"),
    path("characters/charts/<slug:chart>", views.main_interactive_chart),
    path("characters/<slug:name>/", views.reftype_stats, name="ch-stats"),
    path("characters/<slug:name>/charts/<slug:chart>", views.reftype_interactive_chart),
    # Classes
    path("classes/", views.classes, name="classes"),
    path("classes/charts/<slug:chart>", views.main_interactive_chart),
    path("classes/<slug:name>/", views.reftype_stats, name="cl-stats"),
    path("classes/<slug:name>/charts/<slug:chart>", views.reftype_interactive_chart),
    # Skills
    path("skills/", views.skills, name="skills"),
    path("skills/charts/<slug:chart>", views.main_interactive_chart),
    path("skills/<slug:name>/", views.reftype_stats, name="sk-stats"),
    path("skills/<slug:name>/charts/<slug:chart>", views.reftype_interactive_chart),
    # Magic
    path("magic/", views.magic, name="magic"),
    path("magic/charts/<slug:chart>", views.main_interactive_chart),
    path("magic/<slug:name>/", views.reftype_stats, name="sp-stats"),
    path("magic/<slug:name>/charts/<slug:chart>", views.reftype_interactive_chart),
    # Locations
    path("locations/", views.locations, name="locations"),
    path("locations/charts/<slug:chart>", views.main_interactive_chart),
    path("locations/<slug:name>/", views.reftype_stats, name="lo-stats"),
    path("locations/<slug:name>/charts/<slug:chart>", views.reftype_interactive_chart),
    # Search / misc
    path("search/", views.search, name="search"),
    path("about/", views.about, name="about"),
    # Chapters
    path("chapter/<slug:number>", views.chapter_stats, name="chapters"),
    # Plugins
    path("admin/", admin.site.urls),
    path("stats/", include("stats.urls")),
    path("__debug__/", include("debug_toolbar.urls")),
    path("__reload__", include("django_browser_reload.urls")),
]


if apps.is_installed("pattern_library"):
    urlpatterns += [
        path("pattern-library/", include("pattern_library.urls")),
    ]
