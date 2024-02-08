from django.core.cache import cache
from django.db.models import Count, F, Q, QuerySet, Sum, Func, Value, IntegerField
from django.http import HttpRequest, HttpResponse, Http404
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.text import slugify
from django.views.decorators.cache import cache_page
from django_htmx.middleware import HtmxDetails
from django_tables2 import RequestConfig
from django_tables2.paginators import LazyPaginator
from django_tables2.export.export import TableExport
from django_tables2 import SingleTableMixin
from itertools import chain
from typing import Iterable, Tuple
from stats import charts
from stats.charts import ChartGalleryItem, get_reftype_gallery
from stats.models import Chapter, Character, RefType, RefTypeChapter, TextRef
from stats.queries import annotate_reftype_lengths
from .tables import (
    ChapterRefTable,
    TextRefTable,
    ChapterHtmxTable,
    CharacterHtmxTable,
    ReftypeMentionsHtmxTable,
)
from .forms import SearchForm, MAX_CHAPTER_NUM


class HtmxHttpRequest(HttpRequest):
    htmx: HtmxDetails


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
def overview(request: HtmxHttpRequest) -> HttpResponse:
    config = RequestConfig(request)
    data = Chapter.objects.filter(is_canon=True, is_status_update=False)
    table = ChapterHtmxTable(data)
    config.configure(table)
    table.paginate(
        page=request.GET.get("page", 1),
        per_page=request.GET.get("page_size", 15),
        orphans=5,
    )

    if request.htmx:
        return render(request, "tables/table_partial.html", {"table": table})
    else:
        total_wc = Chapter.objects.aggregate(total_wc=Sum("word_count"))["total_wc"]
        longest_chapter = Chapter.objects.filter(is_canon=True).order_by("-word_count")[
            0
        ]
        shortest_chapter = Chapter.objects.filter(is_canon=True).order_by("word_count")[
            0
        ]
        word_counts = (
            Chapter.objects.filter(is_canon=True)
            .order_by("word_count")
            .values_list("word_count", flat=True)
        )

        def median(values: list[int]) -> float:
            length = len(values)
            if length % 2 == 0:
                return sum(values[int(length / 2 - 1) : int(length / 2 + 1)]) / 2.0
            else:
                return values[int(length / 2)]

        median_chapter_word_count = median(word_counts)
        avg_chapter_word_count = sum(word_counts) / len(word_counts)

        context = {
            "gallery": charts.word_count_charts,
            "stats": [
                HeadlineStat("Total Word Count", f"{total_wc:,}", units=" words"),
                HeadlineStat(
                    "Median Word Count per Chapter",
                    f"{round(median_chapter_word_count):,}",
                    units=" words",
                ),
                HeadlineStat(
                    "Average Word Count per Chapter",
                    f"{round(avg_chapter_word_count):,}",
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
            "table": table,
        }
        return render(request, "pages/overview.html", context)


@cache_page(60 * 60 * 24)
def characters(request: HtmxHttpRequest) -> HttpResponse:
    config = RequestConfig(request)
    data = Character.objects.all()
    table = CharacterHtmxTable(data)
    config.configure(table)
    table.paginate(
        page=request.GET.get("page", 1),
        per_page=request.GET.get("page_size", 15),
        orphans=5,
    )

    if request.htmx:
        return render(request, "tables/table_partial.html", {"table": table})
    else:
        char_count = RefType.objects.filter(type=RefType.CHARACTER).aggregate(
            char_count=Count("name")
        )["char_count"]

        species_count = Character.objects.values("species").distinct().count()

        chapter_with_most_char_refs = (
            TextRef.objects.filter(type__type=RefType.CHARACTER)
            .annotate(
                title=F("chapter_line__chapter__title"),
                url=F("chapter_line__chapter__source_url"),
            )
            .select_related("title")
            .values("title", "url")
            .annotate(count=Count("title"))
            .order_by("-count")[0]
        )

        context = {
            "gallery": charts.character_charts,
            "stats": [
                HeadlineStat(
                    "Total Number of Characters", f"{char_count:,}", units=" characters"
                ),
                HeadlineStat(
                    "Chapter with the Most Character Mentions",
                    f"{chapter_with_most_char_refs['count']}",
                    render_to_string(
                        "patterns/atoms/link/link.html",
                        context=dict(
                            text=chapter_with_most_char_refs["title"],
                            href=chapter_with_most_char_refs["url"],
                            external=True,
                        ),
                    ),
                    units=" character mentions",
                ),
                HeadlineStat(
                    "Number of Character Species",
                    f"{species_count:,}",
                    f"out of {len(Character.SPECIES)} known species",
                    units=" species",
                ),
            ],
            "table": table,
        }
        return render(request, "pages/characters.html", context)


@cache_page(60 * 60 * 24)
def classes(request: HtmxHttpRequest) -> HttpResponse:
    config = RequestConfig(request)
    data = annotate_reftype_lengths(RefType.objects.filter(type=RefType.CLASS))
    table = ReftypeMentionsHtmxTable(data)
    config.configure(table)
    table.paginate(
        page=request.GET.get("page", 1),
        per_page=request.GET.get("page_size", 15),
        orphans=5,
    )

    if request.htmx:
        return render(request, "tables/table_partial.html", {"table": table})
    else:
        longest_class_name_by_chars = RefType.objects.filter(
            type=RefType.CLASS
        ).order_by("-name__length")[0]

        longest_class_name_by_words = (
            RefType.objects.filter(type=RefType.CLASS)
            .annotate(
                words=Func(F("name"), Value(r"\s+"), function="regexp_split_to_array")
            )
            .annotate(
                word_count=Func(
                    F("words"), 1, function="array_length", output_field=IntegerField()
                )
            )
            .order_by("-word_count")
        )[0]

        chapter_with_most_class_refs = (
            TextRef.objects.filter(type__type=RefType.CLASS)
            .annotate(
                title=F("chapter_line__chapter__title"),
                url=F("chapter_line__chapter__source_url"),
            )
            .select_related("title")
            .values("title", "url")
            .annotate(count=Count("title"))
            .order_by("-count")[0]
        )

        context = {
            "gallery": charts.class_charts,
            "stats": [
                HeadlineStat(
                    "Longest Class Name (by words)",
                    f"{longest_class_name_by_words.word_count}",
                    f"{longest_class_name_by_words.name}",
                    units=" words",
                ),
                HeadlineStat(
                    "Longest Class Name (by letters)",
                    f"{len(longest_class_name_by_chars.name)}",
                    f"{longest_class_name_by_chars.name}",
                    units=" letters",
                ),
                HeadlineStat(
                    "Chapter with the Most Class Mentions",
                    f"{chapter_with_most_class_refs['count']}",
                    render_to_string(
                        "patterns/atoms/link/link.html",
                        context=dict(
                            text=chapter_with_most_class_refs["title"],
                            href=chapter_with_most_class_refs["url"],
                            external=True,
                        ),
                    ),
                    units=" [Class] mentions",
                ),
            ],
            "table": table,
        }
        return render(request, "pages/classes.html", context)


@cache_page(60 * 60 * 24)
def skills(request: HtmxHttpRequest) -> HttpResponse:
    config = RequestConfig(request)
    data = annotate_reftype_lengths(RefType.objects.filter(type=RefType.SKILL))
    table = ReftypeMentionsHtmxTable(data)
    config.configure(table)
    table.paginate(
        page=request.GET.get("page", 1),
        per_page=request.GET.get("page_size", 15),
        orphans=5,
    )

    if request.htmx:
        return render(request, "tables/table_partial.html", {"table": table})
    else:
        longest_skill_name_by_characters = RefType.objects.filter(
            type=RefType.SKILL
        ).order_by("-name__length")[0]

        longest_skill_name_by_words = (
            RefType.objects.filter(type=RefType.SKILL)
            .annotate(
                words=Func(F("name"), Value(r"\s+"), function="regexp_split_to_array")
            )
            .annotate(
                word_count=Func(
                    F("words"), 1, function="array_length", output_field=IntegerField()
                )
            )
            .order_by("-word_count")
        )[0]

        chapter_with_most_skill_refs = (
            TextRef.objects.filter(type__type=RefType.SKILL)
            .annotate(
                title=F("chapter_line__chapter__title"),
                url=F("chapter_line__chapter__source_url"),
            )
            .select_related("title")
            .values("title", "url")
            .annotate(count=Count("title"))
            .order_by("-count")[0]
        )

        context = {
            "gallery": charts.skill_charts,
            "stats": [
                HeadlineStat(
                    "Longest [Skill] Name (by words)",
                    f"{longest_skill_name_by_words.word_count}",
                    f"{longest_skill_name_by_words.name}",
                    units=" words",
                ),
                HeadlineStat(
                    "Longest [Skill] Name (by letters)",
                    f"{len(longest_skill_name_by_characters.name)}",
                    f"{longest_skill_name_by_characters.name}",
                    units=" letters",
                ),
                HeadlineStat(
                    "Chapter with the Most [Skill] Mentions",
                    f"{chapter_with_most_skill_refs['count']}",
                    render_to_string(
                        "patterns/atoms/link/link.html",
                        context=dict(
                            text=chapter_with_most_skill_refs["title"],
                            href=chapter_with_most_skill_refs["url"],
                            external=True,
                        ),
                    ),
                    units=" [Skill] mentions",
                ),
            ],
            "table": table,
        }
        return render(request, "pages/skills.html", context)


@cache_page(60 * 60 * 24)
def magic(request: HtmxHttpRequest) -> HttpResponse:
    config = RequestConfig(request)
    data = annotate_reftype_lengths(RefType.objects.filter(type=RefType.SPELL))
    table = ReftypeMentionsHtmxTable(data)
    config.configure(table)
    table.paginate(
        page=request.GET.get("page", 1),
        per_page=request.GET.get("page_size", 15),
        orphans=5,
    )

    if request.htmx:
        return render(request, "tables/table_partial.html", {"table": table})
    else:
        longest_spell_name_by_characters = RefType.objects.filter(
            type=RefType.SPELL
        ).order_by("-name__length")[0]

        longest_spell_name_by_words = (
            RefType.objects.filter(type=RefType.SPELL)
            .annotate(
                words=Func(F("name"), Value(r"\s+"), function="regexp_split_to_array")
            )
            .annotate(
                word_count=Func(
                    F("words"), 1, function="array_length", output_field=IntegerField()
                )
            )
            .order_by("-word_count")
        )[0]

        chapter_with_most_spell_refs = (
            TextRef.objects.filter(type__type=RefType.SPELL)
            .annotate(
                title=F("chapter_line__chapter__title"),
                url=F("chapter_line__chapter__source_url"),
            )
            .select_related("title")
            .values("title", "url")
            .annotate(count=Count("title"))
            .order_by("-count")[0]
        )

        context = {
            "gallery": charts.magic_charts,
            "stats": [
                HeadlineStat(
                    "Longest [Spell] Name (by words)",
                    f"{longest_spell_name_by_words.word_count}",
                    f"{longest_spell_name_by_words.name}",
                    units=" words",
                ),
                HeadlineStat(
                    "Longest [Spell] Name (by letters)",
                    f"{len(longest_spell_name_by_characters.name)}",
                    f"{longest_spell_name_by_characters.name}",
                    units=" letters",
                ),
                HeadlineStat(
                    "Chapter with the Most [Spell] Mentions",
                    f"{chapter_with_most_spell_refs['count']}",
                    render_to_string(
                        "patterns/atoms/link/link.html",
                        context=dict(
                            text=chapter_with_most_spell_refs["title"],
                            href=chapter_with_most_spell_refs["url"],
                            external=True,
                        ),
                    ),
                    units=" [Spell] mentions",
                ),
            ],
            "table": table,
        }
        return render(request, "pages/magic.html", context)


def main_interactive_chart(request: HtmxHttpRequest, chart: str):
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


def match_reftype_str(s: str) -> str | None:
    match s:
        case "characters":
            return RefType.CHARACTER
        case "classes":
            return RefType.CLASS
        case "skills":
            return RefType.SKILL
        case "magic":
            return RefType.SPELL
        case _:
            return None


def reftype_interactive_chart(request: HtmxHttpRequest, name: str, chart: str):
    stat_root = request.path.split("/")[1].strip().lower()
    rt_type = match_reftype_str(stat_root)
    rt = RefType.objects.get(Q(slug__istartswith=name) & Q(type=rt_type))
    chart_items = get_reftype_gallery(rt)

    for c in chart_items:
        if chart == c.title_slug:
            context = {
                "chart": c.get_fig().to_html(full_html=False, include_plotlyjs="cdn")
            }
            return render(request, "pages/interactive_chart.html", context)

    raise Http404()


def reftype_stats(request: HtmxHttpRequest, name: str):
    stat_root = request.path.split("/")[1].strip().lower()
    rt_type = match_reftype_str(stat_root)
    rt = RefType.objects.get(Q(slug__istartswith=name) & Q(type=rt_type))
    context = {"title": rt.name, "gallery": get_reftype_gallery(rt)}
    return render(request, "pages/reftype_gallery.html", context)


def search(request: HtmxHttpRequest) -> HttpResponse:
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
def about(request: HtmxHttpRequest) -> HttpResponse:
    return render(request, "pages/about.html")
