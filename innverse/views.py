from django.db.models import Q
from django.shortcuts import render
from django.views.decorators.cache import cache_page
from django_tables2 import SingleTableView, LazyPaginator
from django_tables2.export.export import TableExport
from django_tables2.export.views import ExportMixin
from stats.charts import word_count_charts, character_charts, class_charts
from stats.models import TextRef
from .tables import TextRefTable
from .forms import SearchForm


@cache_page(60 * 60 * 24)
def overview(request):
    context = {
        "plot_groups": {
            "word_counts": {
                "plots": word_count_charts()["plots"],
                "selected_param": "word_count_tab",
                "selected": int(request.GET.get("word_count_tab", 0)),
            }
        }
    }

    return render(request, "pages/overview.html", context)


@cache_page(60 * 60 * 24)
def characters(request):
    context = {
        "plot_groups": {
            "word_counts": {
                "plots": character_charts()["plots"],
                "selected_param": "character_count_tab",
                "selected": int(request.GET.get("character_count_tab", 0)),
            }
        }
    }
    return render(request, "pages/characters.html", context)


@cache_page(60 * 60 * 24)
def classes(request):
    context = {
        "plot_groups": {
            "word_counts": {
                "plots": class_charts()["plots"],
                "selected_param": "class_count_tab",
                "selected": int(request.GET.get("class_count_tab", 0)),
            }
        }
    }
    return render(request, "pages/classes.html", context)


@cache_page(60 * 60 * 24)
def skills(request):
    return render(request, "pages/skills.html")


@cache_page(60 * 60 * 24)
def magic(request):
    return render(request, "pages/magic.html")


class TextRefTableView(ExportMixin, SingleTableView):
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
                & ~Q(color__isnull=form.cleaned_data.get("only_colored_refs"))
            )

            table = TextRefTable(table_data)

            export_format = request.GET.get("_export", None)
            if TableExport.is_valid_format(export_format):
                exporter = TableExport(export_format, table)
                return exporter.response(f"textrefs.{export_format}")

            try:
                table.paginate(
                    page=request.GET.get("page", 1),
                    per_page=request.GET.get("page_size", 15),
                )
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


@cache_page(60 * 60 * 24)
def settings(request):
    return render(request, "pages/settings.html")
