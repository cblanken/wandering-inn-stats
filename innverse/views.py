from django.core.cache import cache
from django.db.models import Count, F, Q, QuerySet, Sum, Func, Value, IntegerField
from django.http import HttpRequest, HttpResponse, Http404
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.cache import cache_page
from django_htmx.middleware import HtmxDetails
from django_tables2 import RequestConfig
from django_tables2.export.export import TableExport
from django_tables2 import SingleTableMixin
from itertools import chain
from typing import Iterable, Tuple
from stats import charts
from stats.charts import ChartGalleryItem, get_reftype_gallery
from stats.models import Alias, Chapter, Character, RefType, RefTypeChapter, TextRef
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
    """The `title_text` parameter overrides the `title` in case a template
    needs to be passed into the `title`"""

    def __init__(
        self,
        title: str,
        value: int | float | str,
        caption: str = "",
        units: str = "",
        popup_info: str | None = None,
    ):
        self.title = title
        self.value = value
        self.units = units
        self.caption = caption
        self.popup_info = popup_info


@cache_page(60 * 60 * 24)
def overview(request: HtmxHttpRequest) -> HttpResponse:
    config = RequestConfig(request)
    query = request.GET.get("q")
    if query:
        data = Chapter.objects.filter(is_canon=True, is_status_update=False).filter(
            Q(title__icontains=query)
            | Q(post_date__icontains=query)
            | Q(word_count__icontains=query)
        )
    else:
        data = Chapter.objects.filter(is_canon=True, is_status_update=False)
    table = ChapterHtmxTable(data)
    config.configure(table)
    table.paginate(
        page=request.GET.get("page", 1),
        per_page=request.GET.get("page_size", 25),
        orphans=5,
    )

    if request.htmx:
        return render(request, table.template_name, dict(table=table))

    total_wc = Chapter.objects.aggregate(total_wc=Sum("word_count"))["total_wc"]
    longest_chapter = Chapter.objects.filter(is_canon=True).order_by("-word_count")[0]
    shortest_chapter = Chapter.objects.filter(is_canon=True).order_by("word_count")[0]
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
            HeadlineStat(
                "Total Word Count",
                f"{total_wc:,}",
                units="words",
                popup_info="The word count for each chapter is calculated by counting the tokens between spaces over the entire text. This is a simple approach, and doesn't account for any of the punctuation-related edge cases. For this reason, you may notice discrepancies between these word counts those posted elsewhere.",
            ),
            HeadlineStat(
                "Median Word Count per Chapter",
                f"{round(median_chapter_word_count):,}",
                units="words",
            ),
            HeadlineStat(
                "Average Word Count per Chapter",
                f"{round(avg_chapter_word_count):,}",
                units="words",
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
                units="words",
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
                units="words",
            ),
        ],
        "table": table,
    }
    return render(request, "pages/overview.html", context)


@cache_page(60 * 60 * 24)
def characters(request: HtmxHttpRequest) -> HttpResponse:
    config = RequestConfig(request)
    query = request.GET.get("q")
    if query:
        data = (
            Character.objects.select_related(
                "ref_type", "ref_type__reftypecomputedview", "first_chapter_appearance"
            )
            .filter(
                Q(ref_type__name__icontains=query)
                | Q(species__icontains=query)
                | Q(status__icontains=query)
                | Q(first_chapter_appearance__title__icontains=query)
            )
            .annotate(mentions=F("ref_type__reftypecomputedview__mentions"))
            .order_by(F("mentions").desc(nulls_last=True))
        )
    else:
        data = (
            Character.objects.select_related(
                "ref_type", "ref_type__reftypecomputedview", "first_chapter_appearance"
            )
            .annotate(mentions=F("ref_type__reftypecomputedview__mentions"))
            .order_by(F("mentions").desc(nulls_last=True))
        )

    table = CharacterHtmxTable(data)
    config.configure(table)
    table.paginate(
        page=request.GET.get("page", 1),
        per_page=request.GET.get("page_size", 25),
        orphans=5,
    )

    if request.htmx:
        return render(request, table.template_name, dict(table=table))

    char_counts = (
        TextRef.objects.filter(type__type=RefType.CHARACTER)
        .select_related("type")
        .values("type__name", "type__character")
        .annotate(
            fca=F("type__character__first_chapter_appearance"),
            count=Count("type__name"),
        )
    )

    chars_with_appearances = char_counts.filter(fca__isnull=False).count()
    chars_mentioned = char_counts.count()

    species_count = Character.objects.values("species").distinct().count()

    chapter_with_most_char_refs = (
        TextRef.objects.filter(type__type=RefType.CHARACTER)
        .select_related("chapter_line__chapter")
        .annotate(
            title=F("chapter_line__chapter__title"),
            url=F("chapter_line__chapter__source_url"),
        )
        .values("title", "url")
        .annotate(count=Count("title"))
        .order_by("-count")[0]
    )

    context = {
        "gallery": charts.character_charts,
        "stats": [
            HeadlineStat(
                "Total Number of Characters",
                f"{chars_with_appearances:,}",
                f"out of {chars_mentioned} total known characters",
                units="character appearances",
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
                units="character mentions",
                popup_info="This is not a count of unique character mentions. It is the total number of mentions for the given chapter. So if a character is mentioned several times throughout the chapter, each instance counts towards the total.",
            ),
            HeadlineStat(
                "Number of Character Species",
                f"{species_count:,}",
                f"out of {len(Character.SPECIES)} known species",
                units="species",
                popup_info='Many species are referenced throughout TWI, but for some species, no specific characters have been mentioned. It\'s possible that they simply haven\'t been encountered yet and may pop up in the future, such as some of the many Lizardfolk variants. However, many of the known species are simply extinct. This is what causes the discrepancy between the character "species" count and the "known species".\nThe "known species" count includes all species. Even those that have no associated characters.',
            ),
        ],
        "table": table,
    }
    return render(request, "pages/characters.html", context)


def get_reftype_table_data(
    query: str | None, rt_type: str, order_by="mentions"
) -> QuerySet[RefType]:
    if query:
        rt_data = (
            RefType.objects.select_related("reftypecomputedview")
            .annotate(mentions=F("reftypecomputedview__mentions"))
            .filter(type=rt_type, name__icontains=query)
            .order_by(F(order_by).desc(nulls_last=True))
        )
    else:
        rt_data = (
            RefType.objects.select_related("reftypecomputedview")
            .annotate(mentions=F("reftypecomputedview__mentions"))
            .filter(type=rt_type)
            .order_by(F("mentions").desc(nulls_last=True))
        )

    return rt_data


@cache_page(60 * 60 * 24)
def classes(request: HtmxHttpRequest) -> HttpResponse:
    config = RequestConfig(request)
    query = request.GET.get("q")
    rt_data = get_reftype_table_data(query, RefType.CLASS)

    table = ReftypeMentionsHtmxTable(rt_data)
    config.configure(table)
    table.paginate(
        page=request.GET.get("page", 1),
        per_page=request.GET.get("page_size", 25),
        orphans=5,
    )

    if request.htmx:
        return render(request, table.template_name, dict(table=table))

    longest_class_name_by_chars = rt_data.order_by("-letter_count")[0]
    longest_class_name_by_words = rt_data.order_by("-word_count")[0]

    chapter_with_most_class_refs = (
        TextRef.objects.filter(type__type=RefType.CLASS)
        .annotate(
            title=F("chapter_line__chapter__title"),
            url=F("chapter_line__chapter__source_url"),
        )
        .select_related("title")
        .values("title", "url")
        .annotate(mentions=Count("title"))
        .order_by("-mentions")[0]
    )

    context = {
        "gallery": charts.class_charts,
        "stats": [
            HeadlineStat(
                "Longest Class Name (by words)",
                f"{longest_class_name_by_words.word_count}",
                f"{longest_class_name_by_words.name}",
                units="words",
            ),
            HeadlineStat(
                "Longest Class Name (by letters)",
                f"{len(longest_class_name_by_chars.name)}",
                f"{longest_class_name_by_chars.name}",
                units="letters",
                popup_info="This count includes punctuation as well as letters.",
            ),
            HeadlineStat(
                "Chapter with the Most Class Mentions",
                f"{chapter_with_most_class_refs['mentions']}",
                render_to_string(
                    "patterns/atoms/link/link.html",
                    context=dict(
                        text=chapter_with_most_class_refs["title"],
                        href=chapter_with_most_class_refs["url"],
                        external=True,
                    ),
                ),
                units="[Class] mentions",
                popup_info="This count includes every instance of a mentioned [Class]. Meaning if a [Class] occurs multiple times throughout a chapter, each instance is counted.",
            ),
        ],
        "table": table,
    }

    return render(request, "pages/classes.html", context)


@cache_page(60 * 60 * 24)
def skills(request: HtmxHttpRequest) -> HttpResponse:
    config = RequestConfig(request)
    query = request.GET.get("q")
    rt_data = get_reftype_table_data(query, RefType.SKILL)

    table = ReftypeMentionsHtmxTable(rt_data)
    config.configure(table)
    table.paginate(
        page=request.GET.get("page", 1),
        per_page=request.GET.get("page_size", 25),
        orphans=5,
    )

    if request.htmx:
        return render(request, table.template_name, dict(table=table))

    longest_skill_name_by_chars = rt_data.order_by("-letter_count")[0]
    longest_skill_name_by_words = rt_data.order_by("-word_count")[0]

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
                units="words",
            ),
            HeadlineStat(
                "Longest [Skill] Name (by letters)",
                f"{len(longest_skill_name_by_chars.name)}",
                f"{longest_skill_name_by_chars.name}",
                units="letters",
                popup_info="This count includes punctuation as well as letters.",
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
                units="[Skill] mentions",
                popup_info="This count includes every instance of a mentioned [Skill]. Meaning if a [Skill] occurs multiple times throughout a chapter, each instance is counted.",
            ),
        ],
        "table": table,
    }

    return render(request, "pages/skills.html", context)


@cache_page(60 * 60 * 24)
def magic(request: HtmxHttpRequest) -> HttpResponse:
    config = RequestConfig(request)
    query = request.GET.get("q")
    rt_data = get_reftype_table_data(query, RefType.SPELL)

    table = ReftypeMentionsHtmxTable(rt_data)
    config.configure(table)
    table.paginate(
        page=request.GET.get("page", 1),
        per_page=request.GET.get("page_size", 25),
        orphans=5,
    )

    if request.htmx:
        return render(request, table.template_name, dict(table=table))

    longest_spell_name_by_chars = rt_data.order_by("-letter_count")[0]
    longest_spell_name_by_words = rt_data.order_by("-word_count")[0]

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
                units="words",
            ),
            HeadlineStat(
                "Longest [Spell] Name (by letters)",
                f"{len(longest_spell_name_by_chars.name)}",
                f"{longest_spell_name_by_chars.name}",
                units="letters",
                popup_info="This count includes punctuation as well as letters.",
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
                units="[Spell] mentions",
                popup_info="This count includes every instance of a mentioned [Spell]. Meaning if a [Spell] occurs multiple times throughout a chapter, each instance is counted.",
            ),
        ],
        "table": table,
    }

    return render(request, "pages/magic.html", context)


@cache_page(60 * 60 * 24)
def locations(request: HtmxHttpRequest) -> HttpResponse:
    config = RequestConfig(request)
    query = request.GET.get("q")
    rt_data = get_reftype_table_data(query, RefType.LOCATION)

    table = ReftypeMentionsHtmxTable(rt_data or [])
    config.configure(table)
    table.paginate(
        page=int(request.GET.get("page", 1)),
        per_page=request.GET.get("page_size", 25),
        orphans=5,
    )

    if request.htmx:
        return render(request, table.template_name, {"table": table, "query": query})

    chapter_with_most_location_refs = (
        TextRef.objects.filter(type__type=RefType.LOCATION)
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
        "gallery": charts.location_charts,
        "stats": [
            HeadlineStat(
                "Chapter with the Most Location Mentions",
                f"{chapter_with_most_location_refs['count']}",
                render_to_string(
                    "patterns/atoms/link/link.html",
                    context=dict(
                        text=chapter_with_most_location_refs["title"],
                        href=chapter_with_most_location_refs["url"],
                        external=True,
                    ),
                ),
                units="Location mentions",
            ),
        ],
        "table": table,
        "query": query,
    }

    return render(request, "pages/locations.html", context)


def main_interactive_chart(request: HtmxHttpRequest, chart: str):
    chart_items: Iterable[ChartGalleryItem] = chain(
        charts.word_count_charts,
        charts.character_charts,
        charts.class_charts,
        charts.skill_charts,
        charts.magic_charts,
        charts.location_charts,
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
        case "locations":
            return RefType.LOCATION
        case _:
            return None


def reftype_interactive_chart(request: HtmxHttpRequest, name: str, chart: str):
    stat_root = request.path.split("/")[1].strip().lower()
    rt_type = match_reftype_str(stat_root)
    if len(name) >= 100:
        rt = RefType.objects.get(Q(slug__istartswith=name) & Q(type=rt_type))
    else:
        rt = RefType.objects.get(Q(slug__iexact=name) & Q(type=rt_type))

    chart_items = get_reftype_gallery(rt)

    for c in chart_items:
        if chart == c.title_slug:
            context = {
                "chart": c.get_fig().to_html(full_html=False, include_plotlyjs="cdn"),
            }
            return render(request, "pages/interactive_chart.html", context)

    raise Http404()


def reftype_stats(request: HtmxHttpRequest, name: str):
    stat_root = request.path.split("/")[1].strip().lower()
    rt_type = match_reftype_str(stat_root)
    if len(name) >= 100:
        rt = RefType.objects.get(Q(slug__istartswith=name) & Q(type=rt_type))
    else:
        rt = RefType.objects.get(Q(slug__iexact=name) & Q(type=rt_type))

    chapter_appearances = (
        RefType.objects.select_related("reftypecomputedview")
        .annotate(mentions=F("reftypecomputedview__mentions"))
        .filter(type=RefType.LOCATION)
        .order_by(F("mentions").desc(nulls_last=True))
    )

    mention_count = TextRef.objects.filter(type=rt).count()

    chapter_appearances = RefTypeChapter.objects.filter(type=rt).order_by(
        "chapter__number"
    )
    first_mention_chapter = chapter_appearances.first()
    last_mention_chapter = chapter_appearances.last()

    aliases = Alias.objects.filter(ref_type=rt).order_by("name")

    match rt_type:
        case RefType.CHARACTER:
            character = Character.objects.get(ref_type=rt)
            href = character.wiki_uri
        case RefType.CLASS:
            name = rt.name[1:-1]
            href = f"https://wiki.wanderinginn.com/List_of_Classes/{name[0]}#:~:text={name}"
        case RefType.SKILL:
            name = rt.name[1:-1]
            href = f"https://wiki.wanderinginn.com/Skills#:~:text={name}"
        case RefType.SPELL:
            name = rt.name[1:-1]
            href = f"https://wiki.wanderinginn.com/Spells#:~:text={name}"
        case RefType.LOCATION:
            href = f"https://wiki.wanderinginn.com/{rt.name.replace(' ', '_')}"
        case _:
            href = None

    context = {
        "title": rt.name,
        "link": render_to_string(
            "patterns/atoms/link/link.html",
            context=dict(text="", href=href, size=8, external=True),
        ),
        "aliases": aliases,
        "gallery": get_reftype_gallery(rt),
        "stats": (
            [
                HeadlineStat("Total mentions", mention_count, units="mentions"),
                HeadlineStat(
                    "First mentioned in chapter",
                    render_to_string(
                        "patterns/atoms/link/link.html",
                        context=dict(
                            text=first_mention_chapter.chapter.title,
                            href=first_mention_chapter.chapter.source_url,
                            size=6,
                            external=True,
                        ),
                    ),
                ),
                HeadlineStat(
                    "Last mentioned in chapter",
                    render_to_string(
                        "patterns/atoms/link/link.html",
                        context=dict(
                            text=last_mention_chapter.chapter.title,
                            href=last_mention_chapter.chapter.source_url,
                            size=6,
                            external=True,
                        ),
                    ),
                ),
            ]
            if first_mention_chapter and last_mention_chapter
            else None
        ),
    }
    return render(request, "pages/reftype_page.html", context)


def get_search_result_table(query: dict[str, str]):
    strict_mode = query.get("strict_mode")
    query_filter = query.get("filter")
    if query.get("refs_by_chapter"):
        if strict_mode:
            ref_types: QuerySet[RefType] = RefType.objects.filter(
                Q(name=query.get("type_query")) & Q(type=query.get("type"))
            )
        else:
            ref_types: QuerySet[RefType] = RefType.objects.filter(
                Q(name__icontains=query.get("type_query")) & Q(type=query.get("type"))
            )

        reftype_chapters = RefTypeChapter.objects.filter(
            Q(type__in=ref_types)
            & Q(chapter__number__gte=query.get("first_chapter"))
            & Q(
                chapter__number__lte=query.get(
                    "last_chapter",
                    int(
                        Chapter.objects.values_list("number").order_by("-number")[0][0]
                    ),
                )
            )
        )

        if query_filter:
            reftype_chapters = reftype_chapters.filter(
                type__name__icontains=query_filter
            )

        table_data = []
        for rt in ref_types:
            chapter_data = reftype_chapters.filter(type=rt).values_list(
                "chapter__title", "chapter__source_url"
            )

            rc_data = {
                "name": rt.name,
                "type": rt.type,
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
                Q(type__type=query.get("type"))
                & Q(chapter_line__chapter__number__gte=query.get("first_chapter"))
                & Q(
                    chapter_line__chapter__number__lte=query.get(
                        "last_chapter",
                        int(Chapter.objects.order_by("-number")[0].number),
                    )
                )
            )
        )

        if query.get("type_query"):
            if strict_mode:
                table_data = table_data.filter(type__name=query.get("type_query"))
            else:
                table_data = table_data.filter(
                    type__name__icontains=query.get("type_query")
                )

        if query.get("text_query"):
            table_data = table_data.filter(
                chapter_line__text__icontains=query.get("text_query")
            )

        if query.get("only_colored_refs"):
            table_data = table_data.filter(color__isnull=False)

        if query_filter:
            table_data = table_data.filter(
                Q(name__icontains=query_filter)
                | Q(text__icontains=query_filter)
                | Q(title__icontains=query_filter)
            )

        table = TextRefTable(table_data)

    return table


def search(request: HtmxHttpRequest) -> HttpResponse:
    if request.method == "GET" and bool(request.GET):
        query = request.GET.copy()
        query["first_chapter"] = query.get("first_chapter", 0)
        query["last_chapter"] = query.get("last_chapter", MAX_CHAPTER_NUM)
        query["filter"] = query.get("q")

        config = RequestConfig(request)

        if request.htmx:
            table = get_search_result_table(query)
            config.configure(table)
            table.paginate(
                page=request.GET.get("page", 1),
                per_page=request.GET.get("page_size", 25),
                orphans=5,
            )
            return render(request, table.template_name, {"table": table})

        form = SearchForm(query)
        if form.is_valid():
            table = get_search_result_table(query)
            config.configure(table)
            table.paginate(
                page=request.GET.get("page", 1),
                per_page=request.GET.get("page_size", 25),
                orphans=5,
            )
            export_format = request.GET.get("_export", None)
            if TableExport.is_valid_format(export_format):
                exporter = TableExport(export_format, table)
                return exporter.response(f"twi_text_refs.{export_format}")

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
