import datetime as dt
from itertools import chain
from typing import Iterable, Tuple

from django.db.models import Count, F, Q, Sum, Window
from django.db.models.functions import Lag
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.text import slugify
from django_htmx.middleware import HtmxDetails
from django_tables2 import RequestConfig, tables
from django_tables2.export.export import TableExport

from innverse.settings import TWI_MIN_REFTYPE_MENTIONS
from stats import charts
from stats.charts import ChartGalleryItem, get_reftype_gallery
from stats.models import Alias, Chapter, Character, RefType, RefTypeChapter, TextRef

from .forms import ChapterFilterForm, SearchForm
from .table_search import (
    get_chapterline_table,
    get_chapterref_table,
    get_character_table,
    get_reftype_table_data,
    get_textref_table,
)
from .tables import (
    ChapterHtmxTable,
    ReftypeHtmxTable,
)

DEFAULT_TABLE_PAGINATION_OPTS = {
    "page": 1,
    "per_page": 20,
    "orphans": 5,
}

MAX_TABLE_ROWS = 1000


def config_table_request(request: HttpRequest, table: tables.Table) -> RequestConfig:
    if request.GET.get("show_all_rows"):
        if len(table.rows) < MAX_TABLE_ROWS:
            config = RequestConfig(request, paginate=False)
        else:
            pagination_opts = DEFAULT_TABLE_PAGINATION_OPTS | {"per_page": MAX_TABLE_ROWS}
            config = RequestConfig(request, paginate=pagination_opts)
    else:
        config = RequestConfig(request, paginate=DEFAULT_TABLE_PAGINATION_OPTS)

    return config


def title_nbsp(s: str) -> str:
    """Return a string replacing targeted spaces with the &nbsp; HTML entities
    to improve the wrapping of titles"""
    return s.replace("Pt. ", "Pt.&nbsp;")


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
    ) -> None:
        self.title = title
        self.value = value
        self.units = units
        self.caption = caption
        self.popup_info = popup_info


def parse_chapter_params(req: HttpRequest) -> Tuple[Chapter | None, Chapter | None]:
    first_chapter_num = last_chapter_num = None
    try:
        if num := req.GET.get("first_chapter"):
            first_chapter_num = int(num)
        if num := req.GET.get("last_chapter"):
            last_chapter_num = int(num)
    except (ValueError, TypeError):
        # TODO: log error
        pass

    first_chapter = last_chapter = None
    try:
        if first_chapter_num:
            first_chapter = Chapter.objects.get(number=first_chapter_num)
        if last_chapter_num:
            last_chapter = Chapter.objects.get(number=last_chapter_num)
    except Chapter.DoesNotExist:
        # TODO log error / render error message
        pass

    return (first_chapter, last_chapter)


def overview(request: HtmxHttpRequest) -> HttpResponse:
    query = request.GET.get("q")
    if query:
        chapter_data = (
            Chapter.objects.filter(is_status_update=False).filter(Q(title__icontains=query)).order_by("post_date")
        )
    else:
        chapter_data = Chapter.objects.filter(is_status_update=False)
    table = ChapterHtmxTable(chapter_data)

    config = config_table_request(request, table)
    config.configure(table)

    if request.htmx:
        return render(request, "tables/htmx_table.html", {"table": table})

    # Only filter for canon chapter data after Chapter table is configured
    chapter_data = chapter_data.filter(is_canon=True)

    total_wc = Chapter.objects.filter(is_canon=True).aggregate(total_wc=Sum("word_count"))["total_wc"]
    longest_chapter = Chapter.objects.filter(is_canon=True).order_by("-word_count")[0]
    shortest_chapter = Chapter.objects.filter(is_canon=True).order_by("word_count")[0]
    word_counts = Chapter.objects.filter(is_canon=True).order_by("word_count").values_list("word_count", flat=True)

    def median(values: list[int]) -> float:
        length = len(values)
        if length % 2 == 0:
            return sum(values[int(length / 2 - 1) : int(length / 2 + 1)]) / 2.0
        return values[int(length / 2)]

    median_chapter_word_count = median(word_counts)
    avg_chapter_word_count = sum(word_counts) / len(word_counts)

    first_chapter = chapter_data.first()
    latest_chapter = chapter_data.last()

    delta_since_first_chapter_release: dt.timedelta = dt.datetime.now(tz=dt.timezone.utc) - first_chapter.post_date
    delta_since_latest_chapter_release: dt.timedelta = dt.datetime.now(tz=dt.timezone.utc) - latest_chapter.post_date
    latest_chapter.post_date - first_chapter.post_date

    longest_release_gap_chapters = (
        Chapter.objects.annotate(
            prev_chapter_number=Window(expression=Lag("number", offset=1)),
            prev_post_date=Window(expression=Lag("post_date", offset=1), order_by="post_date"),
        )
        .annotate(release_cadence=F("post_date") - F("prev_post_date"))
        .filter(release_cadence__isnull=False)
        .order_by("-release_cadence")
    )

    longest_release_chapter_to = longest_release_gap_chapters.first()
    longest_release_chapter_from = Chapter.objects.get(number=longest_release_chapter_to.prev_chapter_number)
    longest_release_gap: dt.timedelta = longest_release_chapter_to.post_date - longest_release_chapter_from.post_date

    context = {
        "gallery": charts.get_word_count_charts(),
        "stats": [
            HeadlineStat(
                "Total Word Count",
                f"{total_wc:,}",
                units="words",
                popup_info="The word count for each chapter is calculated by splitting the text by the whitespace between words. This is a simple approach, and doesn't account for any punctuation-related edge cases, but it is the most common method for counting words. For this reason, you may notice differences between these word counts those posted elsewhere. Note this count excludes any non-canon chapters as well.",
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
                    "patterns/atoms/link/stat_link.html",
                    context={
                        "text": title_nbsp(longest_chapter.title),
                        "href": reverse("chapters", args=[longest_chapter.number]),
                        "fit": True,
                    },
                ),
                units="words",
            ),
            HeadlineStat(
                "Shortest Chapter",
                f"{shortest_chapter.word_count:,}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context={
                        "text": title_nbsp(shortest_chapter.title),
                        "href": reverse("chapters", args=[shortest_chapter.number]),
                        "fit": True,
                    },
                ),
                units="words",
            ),
            HeadlineStat(
                "First chapter published",
                delta_since_first_chapter_release.days,
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context={
                        "text": title_nbsp(first_chapter.title),
                        "href": reverse("chapters", args=[first_chapter.number]),
                        "fit": True,
                    },
                ),
                units="days ago",
            )
            if first_chapter
            else None,
            HeadlineStat(
                "Latest chapter published",
                delta_since_latest_chapter_release.days,
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context={
                        "text": title_nbsp(latest_chapter.title),
                        "href": reverse("chapters", args=[latest_chapter.number]),
                        "fit": True,
                    },
                ),
                units="days ago",
                popup_info="This is the last chapter analyzed by the application. You can expect it to be a couple chapters behind the latest public release. This allows time for updates to be made to the Wiki and reduce the need for manual analysis of new chapters.",
            )
            if latest_chapter
            else None,
            HeadlineStat(
                "Total canon chapters published",
                chapter_data.count(),
                units="chapters",
            ),
            HeadlineStat(
                "Longest chapter release gap",
                f"{longest_release_gap.days} days and {longest_release_gap.seconds // 3600} hours",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context={
                        "text": title_nbsp(longest_release_chapter_from.title),
                        "href": reverse("chapters", args=[longest_release_chapter_from.number]),
                        "fit": True,
                    },
                )
                + "<div>→</div>"
                + render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context={
                        "text": title_nbsp(longest_release_chapter_to.title),
                        "href": reverse("chapters", args=[longest_release_chapter_to.number]),
                        "fit": True,
                    },
                ),
            ),
        ],
        "table": table,
    }
    return render(request, "pages/overview.html", context)


def characters(request: HtmxHttpRequest) -> HttpResponse:
    table = get_character_table(request.GET)
    config = config_table_request(request, table)
    config.configure(table)

    if request.htmx:
        return render(request, "tables/htmx_table.html", {"table": table})

    char_counts = (
        TextRef.objects.filter(type__type=RefType.Type.CHARACTER)
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
        TextRef.objects.filter(type__type=RefType.Type.CHARACTER, chapter_line__chapter__is_canon=True)
        .select_related("chapter_line__chapter")
        .annotate(
            title=F("chapter_line__chapter__title"),
            url=F("chapter_line__chapter__source_url"),
            number=F("chapter_line__chapter__number"),
        )
        .values("title", "url", "number")
        .annotate(count=Count("title"))
        .order_by("-count")[0]
    )

    context = {
        "gallery": charts.get_character_charts(),
        "stats": [
            HeadlineStat(
                "Total Number of Characters",
                f"{chars_with_appearances:,}",
                f"out of {chars_mentioned} total known characters",
                units="character appearances",
                popup_info="This metric counts how many characters have a known appearance according to the TWI Wiki. Therefore, the total known characters count includes some characters that are mentioned but don't actually have an appearance. To be considered an \"appearance\", a character must clearly be in a scene and interacting even if they're not mentioned by name.",
            ),
            HeadlineStat(
                "Chapter with the Most Character Mentions",
                f"{chapter_with_most_char_refs['count']}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context={
                        "text": title_nbsp(chapter_with_most_char_refs["title"]),
                        "href": reverse("chapters", args=[chapter_with_most_char_refs.get("number")]),
                        "fit": True,
                    },
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


def classes(request: HtmxHttpRequest) -> HttpResponse:
    query = request.GET.get("q")
    rt_table_data = get_reftype_table_data(query, RefType.Type.CLASS)
    table = ReftypeHtmxTable(rt_table_data)

    config = config_table_request(request, table)
    config.configure(table)

    if request.htmx:
        return render(request, "tables/htmx_table.html", {"table": table})

    class_data = RefType.objects.filter(type=RefType.Type.CLASS)
    longest_class_name_by_chars = class_data.order_by("-letter_count")[0]
    longest_class_name_by_words = class_data.order_by("-word_count")[0]
    class_count = class_data.count()

    class_update_data = RefType.objects.filter(type=RefType.Type.CLASS_UPDATE)
    class_update_count = class_update_data.count()

    chapter_with_most_class_refs = (
        TextRef.objects.filter(type__type=RefType.Type.CLASS, chapter_line__chapter__is_canon=True)
        .annotate(
            title=F("chapter_line__chapter__title"),
            url=F("chapter_line__chapter__source_url"),
            number=F("chapter_line__chapter__number"),
        )
        .select_related("title")
        .values("title", "url", "number")
        .annotate(mentions=Count("title"))
        .order_by("-mentions")[0]
    )

    context = {
        "gallery": charts.get_class_charts(),
        "stats": [
            HeadlineStat(
                "Total [Class] count",
                f"{class_count}",
                units="[Classes]",
                popup_info="The number of known [Classes] issued by the [System]",
            ),
            HeadlineStat(
                "[Class] updates",
                f"{class_update_count}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context={
                        "text": "[Class] updates list",
                        "href": f"{reverse('search')}?{urlencode({'type': RefType.Type.CLASS_UPDATE})}",
                        "fit": True,
                        "no_icon": True,
                    },
                ),
                units="[Classes] updated",
                popup_info="The number of unique [Class] update messages issued by the [System]",
            ),
            HeadlineStat(
                "Longest Class Name (by words)",
                f"{longest_class_name_by_words.word_count}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context={
                        "text": f"{longest_class_name_by_words.name}",
                        "href": reverse("cl-stats", args=[longest_class_name_by_words.slug]),
                        "fit": True,
                        "no_icon": True,
                    },
                ),
                units="words",
            ),
            HeadlineStat(
                "Longest Class Name (by letters)",
                f"{len(longest_class_name_by_chars.name)}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context={
                        "text": f"{longest_class_name_by_chars.name}",
                        "href": reverse("cl-stats", args=[longest_class_name_by_chars.slug]),
                        "fit": True,
                        "no_icon": True,
                    },
                ),
                units="letters",
                popup_info="This count includes punctuation as well as letters.",
            ),
            HeadlineStat(
                "Chapter with the Most Class Mentions",
                f"{chapter_with_most_class_refs['mentions']}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context={
                        "text": title_nbsp(chapter_with_most_class_refs["title"]),
                        "href": reverse(
                            "chapters",
                            args=[chapter_with_most_class_refs.get("number")],
                        ),
                        "fit": True,
                        "no_icon": True,
                    },
                ),
                units="[Class] mentions",
                popup_info="This count includes every instance of a mentioned [Class]. Meaning if a [Class] occurs multiple times throughout a chapter, each instance is counted.",
            ),
        ],
        "table": table,
    }

    return render(request, "pages/classes.html", context)


def skills(request: HtmxHttpRequest) -> HttpResponse:
    query = request.GET.get("q")
    rt_data = get_reftype_table_data(query, RefType.Type.SKILL)
    table = ReftypeHtmxTable(rt_data)

    config = config_table_request(request, table)
    config.configure(table)

    if request.htmx:
        return render(request, "tables/htmx_table.html", {"table": table})

    longest_skill_name_by_chars = rt_data.order_by("-letter_count")[0]
    longest_skill_name_by_words = rt_data.order_by("-word_count")[0]

    skill_count = RefType.objects.filter(type=RefType.Type.SKILL).count()
    skill_update_count = RefType.objects.filter(type=RefType.Type.SKILL_UPDATE).count()

    chapter_with_most_skill_refs = (
        TextRef.objects.filter(type__type=RefType.Type.SKILL)
        .annotate(
            title=F("chapter_line__chapter__title"),
            url=F("chapter_line__chapter__source_url"),
            number=F("chapter_line__chapter__number"),
        )
        .select_related("title")
        .values("title", "url", "number")
        .annotate(count=Count("title"))
        .order_by("-count")[0]
    )

    context = {
        "gallery": charts.get_skill_charts(),
        "stats": [
            HeadlineStat(
                "Total [Skill] count",
                f"{skill_count}",
                units="[Skills]",
                popup_info="The number of known [Skills] either used by someone who Levels or issued by the [System]",
            ),
            HeadlineStat(
                "[Skill] update count",
                f"{skill_update_count}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context={
                        "text": "[Skill] updates list",
                        "href": f"{reverse('search')}?{urlencode({'type': RefType.Type.SKILL_UPDATE})}",
                        "fit": True,
                        "no_icon": True,
                    },
                ),
                units="[Skills] updated",
                popup_info="The number of unique Skill update messages issued by the [System]",
            ),
            HeadlineStat(
                "Longest [Skill] Name (by words)",
                f"{longest_skill_name_by_words.word_count}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context={
                        "text": f"{longest_skill_name_by_words.name}",
                        "href": reverse("sk-stats", args=[longest_skill_name_by_words.slug]),
                        "fit": True,
                        "no_icon": True,
                    },
                ),
                units="words",
            ),
            HeadlineStat(
                "Longest [Skill] Name (by letters)",
                f"{len(longest_skill_name_by_chars.name)}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context={
                        "text": f"{longest_skill_name_by_chars.name}",
                        "href": reverse("sk-stats", args=[longest_skill_name_by_chars.slug]),
                        "fit": True,
                        "no_icon": True,
                    },
                ),
                units="letters",
                popup_info="This count includes punctuation as well as letters.",
            ),
            HeadlineStat(
                "Chapter with the Most [Skill] Mentions",
                f"{chapter_with_most_skill_refs['count']}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context={
                        "text": chapter_with_most_skill_refs["title"],
                        "href": reverse("chapters", args=[chapter_with_most_skill_refs["number"]]),
                        "fit": True,
                        "no_icon": True,
                    },
                ),
                units="[Skill] mentions",
                popup_info="This count includes every instance of a mentioned [Skill]. Meaning if a [Skill] occurs multiple times throughout a chapter, each instance is counted.",
            ),
        ],
        "table": table,
    }

    return render(request, "pages/skills.html", context)


def magic(request: HtmxHttpRequest) -> HttpResponse:
    query = request.GET.get("q")
    rt_table_data = get_reftype_table_data(query, RefType.Type.SPELL)
    table = ReftypeHtmxTable(rt_table_data)

    config = config_table_request(request, table)
    config.configure(table)

    if request.htmx:
        return render(request, "tables/htmx_table.html", {"table": table})

    longest_spell_name_by_chars = rt_table_data.order_by("-letter_count")[0]
    longest_spell_name_by_words = rt_table_data.order_by("-word_count")[0]

    spell_data = RefType.objects.filter(type=RefType.Type.SPELL)
    spell_count = spell_data.count()

    spell_update_data = RefType.objects.filter(type=RefType.Type.SPELL_UPDATE)
    spell_update_count = spell_update_data.count()

    chapter_with_most_spell_refs = (
        TextRef.objects.filter(type__type=RefType.Type.SPELL)
        .annotate(
            title=F("chapter_line__chapter__title"),
            url=F("chapter_line__chapter__source_url"),
            number=F("chapter_line__chapter__number"),
        )
        .select_related("title")
        .values("title", "url", "number")
        .annotate(count=Count("title"))
        .order_by("-count")[0]
    )

    context = {
        "gallery": charts.get_magic_charts(),
        "stats": [
            HeadlineStat(
                "Total [Spell] count",
                f"{spell_count}",
                units="[Spells]",
                popup_info="The number of known [Spells] issued by the [System]",
            ),
            HeadlineStat(
                "[Spell] updates",
                f"{spell_update_count}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context={
                        "text": "[Spell] updates list",
                        "href": f"{reverse('search')}?{urlencode({'type': RefType.Type.SPELL_UPDATE})}",
                        "fit": True,
                        "no_icon": True,
                    },
                ),
                units="[Spells] updated",
                popup_info="The number of unique [Spell] update messages issued by the [System]",
            ),
            HeadlineStat(
                "Longest [Spell] Name (by words)",
                f"{longest_spell_name_by_words.word_count}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context={
                        "text": f"{longest_spell_name_by_words.name}",
                        "href": reverse("sp-stats", args=[longest_spell_name_by_words.slug]),
                        "fit": True,
                        "no_icon": True,
                    },
                ),
                units="words",
            ),
            HeadlineStat(
                "Longest [Spell] Name (by letters)",
                f"{len(longest_spell_name_by_chars.name)}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context={
                        "text": f"{longest_spell_name_by_chars.name}",
                        "href": reverse("sp-stats", args=[longest_spell_name_by_chars.slug]),
                        "fit": True,
                        "no_icon": True,
                    },
                ),
                units="letters",
                popup_info="This count includes punctuation as well as letters.",
            ),
            HeadlineStat(
                "Chapter with the Most [Spell] Mentions",
                f"{chapter_with_most_spell_refs['count']}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context={
                        "text": chapter_with_most_spell_refs["title"],
                        "href": reverse("chapters", args=[chapter_with_most_spell_refs["number"]]),
                        "fit": True,
                        "no_icon": True,
                    },
                ),
                units="[Spell] mentions",
                popup_info="This count includes every instance of a mentioned [Spell]. Meaning if a [Spell] occurs multiple times throughout a chapter, each instance is counted.",
            ),
        ],
        "table": table,
    }

    return render(request, "pages/magic.html", context)


def locations(request: HtmxHttpRequest) -> HttpResponse:
    query = request.GET.get("q")
    rt_table_data = get_reftype_table_data(query, RefType.Type.LOCATION)
    table = ReftypeHtmxTable(rt_table_data or [])

    config = config_table_request(request, table)
    config.configure(table)

    if request.htmx:
        return render(request, "tables/htmx_table.html", {"table": table})

    location_data = RefType.objects.filter(type=RefType.Type.LOCATION)
    location_count = location_data.count()

    chapter_with_most_location_refs = (
        TextRef.objects.filter(type__type=RefType.Type.LOCATION)
        .annotate(
            title=F("chapter_line__chapter__title"),
            url=F("chapter_line__chapter__source_url"),
            number=F("chapter_line__chapter__number"),
        )
        .select_related("title")
        .values("title", "url", "number")
        .annotate(count=Count("title"))
        .order_by("-count")[0]
    )

    if request.GET.get("first_chapter") or request.GET.get("last_chapter"):
        form = ChapterFilterForm(request.GET)
    else:
        form = ChapterFilterForm()

    context = {
        "gallery": charts.get_location_charts(),
        "stats": [
            HeadlineStat(
                "Total Location count",
                f"{location_count}",
                units="Locations",
                popup_info="The number of known Locations",
            ),
            HeadlineStat(
                "Chapter with the Most Location Mentions",
                f"{chapter_with_most_location_refs['count']}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context={
                        "text": chapter_with_most_location_refs["title"],
                        "href": reverse("chapters", args=[chapter_with_most_location_refs["number"]]),
                        "fit": True,
                        "no_icon": True,
                    },
                ),
                units="Location mentions",
            ),
        ],
        "table": table,
        "query": query,
        "form": form,
    }

    return render(request, "pages/locations.html", context)


def chapter_stats(request: HtmxHttpRequest, number: int) -> HttpResponse:
    try:
        chapter = Chapter.objects.get(number=number)
        number = int(number)
    except (Chapter.DoesNotExist, ValueError) as e:
        raise Http404() from e

    table_filter = request.GET.get("q", "")
    table_query = {"first_chapter": chapter.number, "last_chapter": chapter.number, "q": table_filter}

    table = get_textref_table(table_query)
    table.hidden_cols = [1]

    config = config_table_request(request, table)
    config.configure(table)

    if request.htmx:
        return render(request, "tables/htmx_table.html", {"table": table})

    textrefs = TextRef.objects.select_related("chapter_line__chapter", "type").filter(
        chapter_line__chapter__number=number,
    )
    rt_counts = (
        textrefs.values("type")
        .annotate(count=Count("type"))
        .order_by("-count")
        .values("type__type", "type__name", "count")
    )

    most_mentioned_characters = rt_counts.filter(type__type=RefType.Type.CHARACTER)
    most_mentioned_classes = rt_counts.filter(type__type=RefType.Type.CLASS)
    most_mentioned_skills = rt_counts.filter(type__type=RefType.Type.SKILL)
    most_mentioned_spells = rt_counts.filter(type__type=RefType.Type.SPELL)
    most_mentioned_locations = rt_counts.filter(type__type=RefType.Type.LOCATION)

    most_mentioned_character = most_mentioned_characters.first()
    most_mentioned_class = most_mentioned_classes.first()
    most_mentioned_skill = most_mentioned_skills.first()
    most_mentioned_spell = most_mentioned_spells.first()
    most_mentioned_location = most_mentioned_locations.first()

    honourable_mentions_max = 4

    context = {
        "title": chapter.title,
        "word_count": chapter.word_count,
        "post_date": chapter.post_date,
        "last_update": chapter.last_update,
        "book_title": chapter.book.title,
        "heading": render_to_string(
            "patterns/atoms/link/link.html",
            context={
                "text": f"Chapter {chapter.title}" if len(chapter.title) < 10 else f"{chapter.title}",
                "href": chapter.source_url,
                "external": True,
            },
        ),
        "table": table,
        "stats": [
            HeadlineStat(
                "Most mentioned character",
                f"{most_mentioned_character.get('count') if most_mentioned_character else 'None Mentioned'}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context={
                        "text": f"{most_mentioned_character.get('type__name')}",
                        "href": reverse(
                            f"{most_mentioned_character.get('type__type').lower()}-stats",
                            args=[slugify(most_mentioned_character.get("type__name"))],
                        ),
                        "fit": True,
                    },
                ),
                units="mentions",
                popup_info=render_to_string(
                    "patterns/atoms/headline_stat_block/mention_info_counts.html",
                    context={
                        "description": "Some honourable mentions",
                        "mention_items": most_mentioned_characters[1:honourable_mentions_max],
                    },
                )
                if most_mentioned_characters[1:honourable_mentions_max]
                else None,
            )
            if most_mentioned_character
            else None,
            HeadlineStat(
                "Most mentioned class",
                f"{most_mentioned_class.get('count') if most_mentioned_class else 'None Mentioned'}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context={
                        "text": f"{most_mentioned_class.get('type__name')}",
                        "href": reverse(
                            f"{most_mentioned_class.get('type__type').lower()}-stats",
                            args=[slugify(most_mentioned_class.get("type__name"))],
                        ),
                        "fit": True,
                    },
                ),
                units="mentions",
                popup_info=render_to_string(
                    "patterns/atoms/headline_stat_block/mention_info_counts.html",
                    context={
                        "description": "Some honourable mentions",
                        "mention_items": most_mentioned_classes[1:honourable_mentions_max],
                    },
                )
                if most_mentioned_classes[1:honourable_mentions_max]
                else None,
            )
            if most_mentioned_class
            else None,
            HeadlineStat(
                "Most mentioned skill",
                f"{most_mentioned_skill.get('count') if most_mentioned_skill else 'None Mentioned'}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context={
                        "text": f"{most_mentioned_skill.get('type__name')}",
                        "href": reverse(
                            f"{most_mentioned_skill.get('type__type').lower()}-stats",
                            args=[slugify(most_mentioned_skill.get("type__name"))],
                        ),
                        "fit": True,
                    },
                ),
                units="mentions",
                popup_info=render_to_string(
                    "patterns/atoms/headline_stat_block/mention_info_counts.html",
                    context={
                        "description": "Some honourable mentions",
                        "mention_items": most_mentioned_skills[1:honourable_mentions_max],
                    },
                )
                if most_mentioned_skills[1:honourable_mentions_max]
                else None,
            )
            if most_mentioned_skill
            else None,
            HeadlineStat(
                "Most mentioned spell",
                f"{most_mentioned_spell.get('count') if most_mentioned_spell else 'None Mentioned'}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context={
                        "text": f"{most_mentioned_spell.get('type__name')}",
                        "href": reverse(
                            f"{most_mentioned_spell.get('type__type').lower()}-stats",
                            args=[slugify(most_mentioned_spell.get("type__name"))],
                        ),
                        "fit": True,
                    },
                ),
                units="mentions",
                popup_info=render_to_string(
                    "patterns/atoms/headline_stat_block/mention_info_counts.html",
                    context={
                        "description": "Some honourable mentions",
                        "mention_items": most_mentioned_spells[1:honourable_mentions_max],
                    },
                )
                if most_mentioned_spells[1:honourable_mentions_max]
                else None,
            )
            if most_mentioned_spell
            else None,
            HeadlineStat(
                "Most mentioned location",
                f"{most_mentioned_location.get('count') if most_mentioned_location else 'None Mentioned'}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context={
                        "text": f"{most_mentioned_location.get('type__name')}",
                        "href": reverse(
                            f"{most_mentioned_location.get('type__type').lower()}-stats",
                            args=[slugify(most_mentioned_location.get("type__name"))],
                        ),
                        "fit": True,
                    },
                ),
                units="mentions",
                popup_info=render_to_string(
                    "patterns/atoms/headline_stat_block/mention_info_counts.html",
                    context={
                        "description": "Some honourable mentions",
                        "mention_items": most_mentioned_locations[1:honourable_mentions_max],
                    },
                )
                if most_mentioned_locations[1:honourable_mentions_max]
                else None,
            )
            if most_mentioned_location
            else None,
        ],
        "query": table_filter,
    }
    return render(request, "pages/chapter_page.html", context)


def main_interactive_chart(request: HtmxHttpRequest, chart: str) -> HttpResponse:
    first_chapter, last_chapter = parse_chapter_params(request)

    chart_items: Iterable[ChartGalleryItem] = chain(
        charts.get_word_count_charts(first_chapter, last_chapter),
        charts.get_character_charts(first_chapter, last_chapter),
        charts.get_class_charts(first_chapter, last_chapter),
        charts.get_skill_charts(first_chapter, last_chapter),
        charts.get_magic_charts(first_chapter, last_chapter),
        charts.get_location_charts(first_chapter, last_chapter),
    )

    if request.GET.get("first_chapter") or request.GET.get("last_chapter"):
        form = ChapterFilterForm(request.GET)
        # TODO check for valid params
    else:
        form = ChapterFilterForm()

    for c in chart_items:
        if chart == c.title_slug:
            fig = c.get_fig()
            context = {
                "chart": (fig.to_html(full_html=False, include_plotlyjs="cdn") if fig else None),
                "form": form,
                "has_chapter_filter": c.has_chapter_filter,
            }
            return render(request, "pages/interactive_chart.html", context)

    raise Http404()


def match_reftype_str(s: str) -> str | None:
    match s:
        case "characters":
            return RefType.Type.CHARACTER
        case "classes":
            return RefType.Type.CLASS
        case "skills":
            return RefType.Type.SKILL
        case "magic":
            return RefType.Type.SPELL
        case "locations":
            return RefType.Type.LOCATION
        case _:
            return None


def reftype_interactive_chart(request: HtmxHttpRequest, name: str, chart: str) -> HttpResponse:
    stat_root = request.path.split("/")[1].strip().lower()
    rt_type = match_reftype_str(stat_root)
    if len(name) >= 100:
        rt = RefType.objects.get(Q(slug__istartswith=name) & Q(type=rt_type))
    else:
        rt = RefType.objects.get(Q(slug__iexact=name) & Q(type=rt_type))

    if request.GET.get("first_chapter") or request.GET.get("last_chapter"):
        form = ChapterFilterForm(request.GET)
        # TODO check for valid params
    else:
        form = ChapterFilterForm()

    first_chapter, last_chapter = parse_chapter_params(request)

    chart_items = get_reftype_gallery(rt, first_chapter, last_chapter)

    for c in chart_items:
        if chart == c.title_slug:
            fig = c.get_fig()

            context = {
                "chart": (fig.to_html(full_html=False, include_plotlyjs="cdn") if fig else None),
                "form": form,
                "has_chapter_filter": c.has_chapter_filter,
            }

            return render(request, "pages/interactive_chart.html", context)

    raise Http404()


def reftype_stats(request: HtmxHttpRequest, name: str) -> HttpResponse:
    stat_root = request.path.split("/")[1].strip().lower()
    rt_type = match_reftype_str(stat_root)

    if len(name) >= 100:
        rt = RefType.objects.get(Q(slug__istartswith=name[:100]) & Q(type=rt_type))
    else:
        rt = RefType.objects.get(Q(slug__iexact=name) & Q(type=rt_type))

    # Table config and pagination
    table_query = {"type": rt.type, "type_query": rt.name, "filter": request.GET.get("q", "")}

    table = get_textref_table(table_query)
    table.hidden_cols = [0]

    config = config_table_request(request, table)
    config.configure(table)

    if request.htmx:
        return render(request, "tables/htmx_table.html", {"table": table})

    chapter_appearances = (
        RefType.objects.select_related("reftypecomputedview")
        .annotate(mentions=F("reftypecomputedview__mentions"))
        .order_by(F("mentions").desc(nulls_last=True))
    )

    mention_count = TextRef.objects.filter(type=rt, chapter_line__chapter__is_canon=True).count()

    chapter_appearances = RefTypeChapter.objects.filter(type=rt, chapter__is_canon=True).order_by("chapter__number")
    first_mention_chapter = chapter_appearances.first()
    last_mention_chapter = chapter_appearances.last()

    aliases = Alias.objects.filter(ref_type=rt).order_by("name")

    match rt_type:
        case RefType.Type.CHARACTER:
            character = Character.objects.get(ref_type=rt)
            href = character.wiki_uri
        case RefType.Type.CLASS:
            name = rt.name[1:-1]
            href = f"https://wiki.wanderinginn.com/List_of_Classes/{name[0]}#:~:text={name}"
        case RefType.Type.SKILL:
            name = rt.name[1:-1]
            href = f"https://wiki.wanderinginn.com/Skills#:~:text={name}"
        case RefType.Type.SPELL:
            name = rt.name[1:-1]
            href = f"https://wiki.wanderinginn.com/Spells#:~:text={name}"
        case RefType.Type.LOCATION:
            href = f"https://wiki.wanderinginn.com/{rt.name.replace(' ', '_')}"
        case _:
            href = None

    context = {
        "name": name,
        "character": character if rt_type == RefType.Type.CHARACTER else None,
        "table": table,
        "title": rt.name,
        "wiki_link": render_to_string(
            "patterns/atoms/link/link.html",
            context={"text": rt.name, "href": href, "external": True},
        ),
        "aliases": aliases,
        "gallery": get_reftype_gallery(rt) if mention_count > TWI_MIN_REFTYPE_MENTIONS else None,
        "stats": (
            [
                HeadlineStat("Total mentions", mention_count, units="mentions"),
                HeadlineStat(
                    "First mentioned in chapter",
                    render_to_string(
                        "patterns/atoms/link/stat_link.html",
                        context={
                            "text": title_nbsp(first_mention_chapter.chapter.title),
                            "href": reverse("chapters", args=[first_mention_chapter.chapter.number]),
                            "fit": True,
                            "no_icon": True,
                        },
                    ),
                ),
                HeadlineStat(
                    "Last mentioned in chapter",
                    render_to_string(
                        "patterns/atoms/link/stat_link.html",
                        context={
                            "text": title_nbsp(last_mention_chapter.chapter.title),
                            "href": reverse("chapters", args=[last_mention_chapter.chapter.number]),
                            "fit": True,
                            "no_icon": True,
                        },
                    ),
                ),
            ]
            if first_mention_chapter and last_mention_chapter
            else None
        ),
    }
    return render(request, "pages/reftype_page.html", context)


def search(request: HtmxHttpRequest) -> HttpResponse:
    if request.method != "GET" or request.GET == {}:
        return render(request, "pages/search.html", {"form": SearchForm()})

    form = SearchForm(request.GET)
    is_valid = form.is_valid()
    if not request.htmx and not is_valid:
        # Form data not valid
        return render(
            request,
            "pages/search_error.html",
            {"error": "Invalid search parameter provided. Please try again."},
        )

    if form.cleaned_data.get("all_contents"):
        table = get_chapterline_table(form.cleaned_data)
    elif form.cleaned_data.get("refs_by_chapter"):
        table = get_chapterref_table(form.cleaned_data)
    else:
        table = get_textref_table(form.cleaned_data)

    config = config_table_request(request, table)
    config.configure(table)

    if request.htmx:
        return render(request, "tables/htmx_table.html", {"table": table})

    # Default search page
    export_format = request.GET.get("_export", None)
    if TableExport.is_valid_format(export_format):
        exporter = TableExport(export_format, table)
        return exporter.response(f"twi_text_refs.{export_format}")

    context = {
        "table": table,
        "form": form,
    }
    return render(request, "pages/search.html", context)


def about(request: HtmxHttpRequest) -> HttpResponse:
    return render(request, "pages/about.html")
