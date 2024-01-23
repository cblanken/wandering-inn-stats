from django.contrib import admin
from django.apps import apps
from django.http import HttpResponseRedirect
from django.urls import path, include, reverse

# from django.shortcuts import redirect

from . import views


def overview_redirect(req):
    return HttpResponseRedirect(reverse(views.overview))


urlpatterns = [
    path("", overview_redirect),
    path("overview/", views.overview),
    path("overview/charts/<slug:chart>", views.interactive_chart),
    path("characters/", views.characters),
    path("characters/charts/<slug:chart>", views.interactive_chart),
    path("classes/", views.classes),
    path("classes/charts/<slug:chart>", views.interactive_chart),
    path("skills/", views.skills),
    path("skills/charts/<slug:chart>", views.interactive_chart),
    path("magic/", views.magic),
    path("magic/charts/<slug:chart>", views.interactive_chart),
    path("search/", views.search),
    path("about/", views.about),
    path("stats/", include("stats.urls")),
    path("admin/", admin.site.urls),
    path("__debug__/", include("debug_toolbar.urls")),
    path("__reload__", include("django_browser_reload.urls")),
]


if apps.is_installed("pattern_library"):
    urlpatterns += [
        path("pattern-library/", include("pattern_library.urls")),
    ]
