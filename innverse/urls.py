from django.apps import apps
from django.contrib import admin
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import include, path, reverse
from django.views.decorators.cache import cache_page

from . import views

CACHE_TIME_TINY = 60
CACHE_TIME_SHORT = 60 * 10
CACHE_TIME_MEDIUM = 60 * 60
CACHE_TIME_LONG = 60 * 60 * 24


def overview_redirect(_req: HttpRequest) -> HttpResponseRedirect:
    return HttpResponseRedirect(reverse("overview"))


app_name = "innverse"
# fmt: off
urlpatterns = [
    # Main page
    path("", overview_redirect),
    path("overview/", cache_page(CACHE_TIME_LONG)(views.overview), name="overview"),
    path("overview/charts/<slug:chart>", cache_page(CACHE_TIME_LONG)(views.main_interactive_chart)),
    # Characters
    path("characters/", cache_page(CACHE_TIME_LONG)(views.characters), name="character"),
    path("characters/charts/<slug:chart>", cache_page(CACHE_TIME_LONG)(views.main_interactive_chart)),
    path("characters/<slug:name>/", cache_page(CACHE_TIME_SHORT)(views.reftype_stats), name="ch-stats"),
    path("characters/<slug:name>/charts/<slug:chart>", cache_page(CACHE_TIME_SHORT)(views.reftype_interactive_chart)),
    # Classes
    path("classes/", views.classes, name="classes"),
    path("classes/charts/<slug:chart>", cache_page(CACHE_TIME_LONG)(views.main_interactive_chart)),
    path("classes/<slug:name>/", cache_page(CACHE_TIME_SHORT)(views.reftype_stats), name="cl-stats"),
    path("classes/<slug:name>/charts/<slug:chart>", cache_page(CACHE_TIME_SHORT)(views.reftype_interactive_chart)),
    # Skills
    path("skills/", views.skills, name="skills"),
    path("skills/charts/<slug:chart>", cache_page(CACHE_TIME_LONG)(views.main_interactive_chart)),
    path("skills/<slug:name>/", cache_page(CACHE_TIME_SHORT)(views.reftype_stats), name="sk-stats"),
    path("skills/<slug:name>/charts/<slug:chart>", cache_page(CACHE_TIME_SHORT)(views.reftype_interactive_chart)),
    # Magic
    path("magic/", views.magic, name="magic"),
    path("magic/charts/<slug:chart>", cache_page(CACHE_TIME_LONG)(views.main_interactive_chart)),
    path("magic/<slug:name>/", cache_page(CACHE_TIME_SHORT)(views.reftype_stats), name="sp-stats"),
    path("magic/<slug:name>/charts/<slug:chart>", cache_page(CACHE_TIME_SHORT)(views.reftype_interactive_chart)),
    # Locations
    path("locations/", views.locations, name="locations"),
    path("locations/charts/<slug:chart>", views.main_interactive_chart),
    path("locations/<slug:name>/", cache_page(CACHE_TIME_SHORT)(views.reftype_stats), name="lo-stats"),
    path("locations/<slug:name>/charts/<slug:chart>", cache_page(CACHE_TIME_SHORT)(views.reftype_interactive_chart)),
    # Search / misc
    path("search/", cache_page(CACHE_TIME_LONG)(views.search), name="search"),
    path("about/", cache_page(CACHE_TIME_LONG)(views.about), name="about"),
    # Chapters
    path("chapter/<slug:number>", cache_page(CACHE_TIME_SHORT)(views.chapter_stats), name="chapters"),
    # Plugins
    path("admin/", admin.site.urls, name="admin"),
    path("stats/", include("stats.urls")),
    path("__debug__/", include("debug_toolbar.urls")),
    path("__reload__", include("django_browser_reload.urls")),
]
# fmt: on


if apps.is_installed("pattern_library"):
    urlpatterns += [
        path("pattern-library/", include("pattern_library.urls")),
    ]
