from django.contrib import admin
from django.apps import apps
from django.http import HttpResponseRedirect
from django.urls import path, include, reverse

from . import views


def overview_redirect(req):
    return HttpResponseRedirect(reverse(views.overview))


app_name = "polls"
urlpatterns = [
    path("", overview_redirect),
    path("overview/", views.overview, name="overview"),
    path("overview/charts/<slug:chart>", views.main_interactive_chart),
    path("characters/", views.characters, name="character"),
    path("characters/charts/<slug:chart>", views.main_interactive_chart),
    path("characters/<slug:name>/", views.reftype_stats),
    path("characters/<slug:name>/charts/<slug:chart>", views.reftype_interactive_chart),
    path("classes/", views.classes, name="classes"),
    path("classes/charts/<slug:chart>", views.main_interactive_chart),
    path("classes/<slug:name>/", views.reftype_stats),
    path("classes/<slug:name>/charts/<slug:chart>", views.reftype_interactive_chart),
    path("skills/", views.skills, name="skills"),
    path("skills/charts/<slug:chart>", views.main_interactive_chart),
    path("skills/<slug:name>/", views.reftype_stats),
    path("skills/<slug:name>/charts/<slug:chart>", views.reftype_interactive_chart),
    path("magic/", views.magic, name="magic"),
    path("magic/charts/<slug:chart>", views.main_interactive_chart),
    path("magic/<slug:name>/", views.reftype_stats),
    path("magic/<slug:name>/charts/<slug:chart>", views.reftype_interactive_chart),
    path("locations/", views.locations, name="locations"),
    path("locations/charts/<slug:chart>", views.main_interactive_chart),
    path("locations/<slug:name>/", views.reftype_stats),
    path("locations/<slug:name>/charts/<slug:chart>", views.reftype_interactive_chart),
    path("search/", views.search, name="search"),
    path("about/", views.about, name="about"),
    path("stats/", include("stats.urls")),
    path("admin/", admin.site.urls),
    path("__debug__/", include("debug_toolbar.urls")),
    path("__reload__", include("django_browser_reload.urls")),
]


if apps.is_installed("pattern_library"):
    urlpatterns += [
        path("pattern-library/", include("pattern_library.urls")),
    ]
