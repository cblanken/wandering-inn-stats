from django.db.models import Q
from django.shortcuts import render
from django.views.decorators.cache import cache_page
from django_tables2.export.export import TableExport
from stats.charts import word_count_charts, character_charts, class_charts
from stats.models import Chapter, RefType, RefTypeChapter, TextRef
from .tables import ChapterRefTable, TextRefTable
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


def search(request):
    if request.method == "GET" and bool(request.GET):
        query = request.GET.copy()
        query["first_chapter"] = query.get("first_chapter", 0)
        query["last_chapter"] = query.get(
            "last_chapter", int(Chapter.objects.all().order_by("-number")[0].number + 1)
        )
        form = SearchForm(query)

        if form.is_valid():
            if form.cleaned_data.get("refs_by_chapter"):
                ref_types: list[RefType] = RefType.objects.filter(
                    Q(name__icontains=form.cleaned_data.get("type_query"))
                    & Q(type=form.cleaned_data.get("type"))
                )

                reftype_chapters = RefTypeChapter.objects.filter(
                    Q(type__in=ref_types)
                    & Q(chapter__number__gte=form.cleaned_data.get("first_chapter"))
                    & Q(
                        chapter__number__lte=form.cleaned_data.get(
                            "last_chapter",
                            int(Chapter.objects.all().order_by("-number")[0].number),
                        )
                    )
                )

                table_data = []
                for rt in ref_types:
                    chapter_data = reftype_chapters.filter(type=rt)
                    chapter_data = chapter_data.values_list(
                        "chapter__title", "chapter__source_url"
                    )

                    rc_data = {
                        "name": rt.name,
                        "chapter_data": chapter_data,
                    }

                    rc_data["count"] = len(rc_data["chapter_data"])

                    if rc_data["chapter_data"]:
                        table_data.append(rc_data)

                table = ChapterRefTable(table_data)
            else:
                # Default TextRefs table data
                table_data = TextRef.objects.filter(
                    Q(type__type=form.cleaned_data.get("type"))
                    & Q(type__name__icontains=form.cleaned_data.get("type_query"))
                    & Q(
                        chapter_line__text__icontains=form.cleaned_data.get(
                            "text_query"
                        )
                    )
                    & Q(
                        chapter_line__chapter__number__gte=form.cleaned_data.get(
                            "first_chapter"
                        )
                    )
                    & Q(
                        chapter_line__chapter__number__lte=form.cleaned_data.get(
                            "last_chapter",
                            int(Chapter.objects.all().order_by("-number")[0].number),
                        )
                    )
                )

                if form.cleaned_data.get("only_colored_refs"):
                    table_data = table_data.filter(color__isnull=False)

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
            context["result_count"] = table_data.count()
            return render(request, "pages/search.html", context)
        else:
            # Form data not valid
            return render(
                request,
                "pages/search_error.html",
                {"error": f"Invalid search parameter provided. Please try again."},
            )
    else:
        return render(request, "pages/search.html", {"form": SearchForm()})


@cache_page(60 * 60 * 24)
def about(request):
    return render(request, "pages/about.html")
