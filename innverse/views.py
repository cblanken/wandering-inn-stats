from django.db.models import Q
from django.shortcuts import render
from django.views.decorators.cache import cache_page
from django_tables2 import SingleTableView, LazyPaginator
from stats.charts import word_count_charts, character_charts, class_charts
from stats.models import TextRef
from .tables import TextRefTable
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


class TextRefView(SingleTableView):
    model = TextRef
    table_class = TextRefTable


def search(request):
    if request.method == "GET" and bool(request.GET):
        form = SearchForm(request.GET.copy())

        if form.is_valid():
            # Query TextRefs per form parameters
            table_data = TextRef.objects.filter(
                Q(type__type=form.cleaned_data.get("type"))
                & Q(type__name__icontains=form.cleaned_data.get("type_query"))
                & Q(chapter_line__text__icontains=form.cleaned_data.get("text_query"))
                & Q(
                    chapter_line__chapter__number__gte=form.cleaned_data.get(
                        "first_chapter"
                    )
                )
                & Q(
                    chapter_line__chapter__number__lte=form.cleaned_data.get(
                        "last_chapter"
                    )
                )
            )

            table = TextRefTable(table_data)
            try:
                table.paginate(page=request.GET.get("page", 1), per_page=15)
            except:
                return render(
                    request,
                    "pages/search_error.html",
                    {"error": "No results for the current search"},
                )

            context = {}
            context["table"] = table
            context["form"] = form
            return render(request, "pages/search.html", context)
        else:
            # Form data not valid
            return render(
                request, "pages/search_error.html", {"error": "Invalid form data"}
            )
    else:
        return render(request, "pages/search.html", {"form": SearchForm()})


@cache_page(60 * 60 * 24)
def about(request):
    return render(request, "pages/about.html")


def settings(request):
    return render(request, "pages/settings.html")
