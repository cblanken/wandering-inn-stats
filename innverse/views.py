from django.core.cache import cache
from django.db.models import Count, F, Q, QuerySet, Sum
from django.http import Http404
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.cache import cache_page
from django_tables2.paginators import LazyPaginator
from django_tables2.export.export import TableExport
from itertools import chain
from typing import Iterable, Tuple
from stats import charts
from stats.charts import ChartGalleryItem
from stats.models import Chapter, Character, RefType, RefTypeChapter, TextRef
from .tables import ChapterRefTable, TextRefTable
from .forms import SearchForm, MAX_CHAPTER_NUM


class HeadlineStat:
    def __init__(
        self,
        title: str,
        value: int | float | str,
        caption: str = "",
        units: str = "",
    ):
        self.title = title
        self.value = value
        self.units = units
        self.caption = caption


@cache_page(60 * 60 * 24)
def overview(request):
    total_wc = Chapter.objects.aggregate(total_wc=Sum("word_count"))["total_wc"]
    longest_chapter = Chapter.objects.filter(is_canon=True).order_by("-word_count")[0]
    shortest_chapter = Chapter.objects.filter(is_canon=True).order_by("word_count")[0]
    word_counts = Chapter.objects.filter(is_canon=True).order_by("word_count")

    def median(qs: QuerySet) -> float:
        len = word_counts.count()
        values = word_counts.values_list("word_count", flat=True)
        if len % 2 == 0:
            return sum(values[int(len / 2 - 1) : int(len / 2 + 1)]) / 2.0
        else:
            return values[int(len / 2)]

    median_chapter_word_count = median(word_counts)

    # return render_to_string(
    #     "patterns/atoms/link/link.html",
    #     context={
    #         "text": f"{record.type.name}",
    #         "href": f"https://wiki.wanderinginn.com/{record.type.name}",
    #         "external": True,
    #     },
    # )

    context = {
        "gallery": charts.word_count_charts,
        "stats": [
            HeadlineStat("Total Word Count", f"{total_wc:,}", units=" words"),
            HeadlineStat(
                "Median Word Count",
                f"{round(median_chapter_word_count):,}",
                units=" words",
            ),
            HeadlineStat(
                "Longest Chapter",
                f"{longest_chapter.word_count:,}",
                render_to_string(
                    "patterns/atoms/link/link.html",
                    context=dict(
                        text=longest_chapter.title,
                        href=longest_chapter.source_url,
                        external=True,
                    ),
                ),
                units=" words",
            ),
            HeadlineStat(
                "Shortest Chapter",
                f"{shortest_chapter.word_count:,}",
                render_to_string(
                    "patterns/atoms/link/link.html",
                    context=dict(
                        text=shortest_chapter.title,
                        href=shortest_chapter.source_url,
                        external=True,
                    ),
                ),
                units=" words",
            ),
        ],
    }
    return render(request, "pages/overview.html", context)


@cache_page(60 * 60 * 24)
def characters(request):
    char_count = RefType.objects.filter(type=RefType.CHARACTER).aggregate(
        char_count=Count("name")
    )["char_count"]

    species_count = Character.objects.values("species").distinct().count()

    context = {
        "gallery": charts.character_charts,
        "stats": [
            HeadlineStat(
                "Total Number of Characters", f"{char_count:,}", units=" characters"
            ),
            HeadlineStat(
                "Number of Character Species",
                f"{species_count:,}",
                f"out of {len(Character.SPECIES)} known species",
                units=" species",
            ),
        ],
    }
    return render(request, "pages/characters.html", context)


@cache_page(60 * 60 * 24)
def classes(request):
    context = {"gallery": charts.class_charts}
    return render(request, "pages/classes.html", context)


@cache_page(60 * 60 * 24)
def skills(request):
    context = {"gallery": charts.skill_charts}
    return render(request, "pages/skills.html", context)


@cache_page(60 * 60 * 24)
def magic(request):
    context = {"gallery": charts.magic_charts}
    return render(request, "pages/magic.html", context)


def interactive_chart(request, chart):
    chart_items: Iterable[ChartGalleryItem] = chain(
        charts.word_count_charts,
        charts.character_charts,
        charts.class_charts,
        charts.skill_charts,
        charts.magic_charts,
    )

    for c in chart_items:
        if chart == c.title_slug:
            context = {
                "chart": c.get_fig().to_html(full_html=False, include_plotlyjs="cdn")
            }
            return render(request, "pages/interactive_chart.html", context)

    raise Http404()


def search(request):
    if request.method == "GET" and bool(request.GET):
        query = request.GET.copy()
        query["first_chapter"] = query.get("first_chapter", 0)
        query["last_chapter"] = query.get("last_chapter", MAX_CHAPTER_NUM)
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
                            int(
                                Chapter.objects.values_list("number").order_by(
                                    "-number"
                                )[0][0]
                            ),
                        )
                    )
                )

                table_data = []
                for rt in ref_types:
                    chapter_data = reftype_chapters.filter(type=rt).values_list(
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
                table_data = (
                    TextRef.objects.select_related("type", "chapter_line__chapter")
                    .annotate(
                        name=F("type__name"),
                        text=F("chapter_line__text"),
                        title=F("chapter_line__chapter__title"),
                        url=F("chapter_line__chapter__source_url"),
                    )
                    .filter(
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
                                int(Chapter.objects.order_by("-number")[0].number),
                            )
                        )
                    )
                )

                if form.cleaned_data.get("only_colored_refs"):
                    table_data = table_data.filter(color__isnull=False)

                table = TextRefTable(table_data)

            export_format = request.GET.get("_export", None)
            if TableExport.is_valid_format(export_format):
                exporter = TableExport(export_format, table)
                return exporter.response(f"twi_text_refs.{export_format}")

            try:
                table.paginate(
                    # paginator_class=LazyPaginator,
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
            # context["result_count"] = table_data.count()
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
