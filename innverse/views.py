from django.db.models import Count, F, Q, QuerySet, Sum, Window
from django.db.models.functions import Lag
from django.http import HttpRequest, HttpResponse, Http404
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.text import slugify
from django_htmx.middleware import HtmxDetails
from django_tables2 import RequestConfig
from django_tables2.export.export import TableExport
from django.urls import NoReverseMatch, reverse
import datetime as dt
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
from .forms import ChapterFilterForm, SearchForm, MAX_CHAPTER_NUM


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
    config = RequestConfig(request)
    query = request.GET.get("q")
    if query:
        chapter_data = (
            Chapter.objects.filter(is_canon=True, is_status_update=False)
            .filter(
                Q(title__icontains=query)
                | Q(post_date__icontains=query)
                | Q(word_count__icontains=query)
            )
            .order_by("post_date")
        )
    else:
        chapter_data = Chapter.objects.filter(is_canon=True, is_status_update=False)
    table = ChapterHtmxTable(chapter_data)
    config.configure(table)
    table.paginate(
        page=request.GET.get("page", 1),
        per_page=request.GET.get("page_size", 25),
        orphans=5,
    )

    if request.htmx:
        return render(request, "tables/htmx_table.html", dict(table=table))

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

    first_chapter = chapter_data.first()
    latest_chapter = chapter_data.last()

    delta_since_first_chapter_release: dt.timedelta = (
        dt.datetime.now(tz=dt.timezone.utc) - first_chapter.post_date
    )
    delta_since_latest_chapter_release: dt.timedelta = (
        dt.datetime.now(tz=dt.timezone.utc) - latest_chapter.post_date
    )
    delta_between_first_and_last_chapters: dt.timedelta = (
        latest_chapter.post_date - first_chapter.post_date
    )

    longest_release_gap_chapters = (
        Chapter.objects.annotate(
            prev_chapter_number=Window(expression=Lag("number", offset=1)),
            prev_post_date=Window(
                expression=Lag("post_date", offset=1), order_by="post_date"
            ),
        )
        .annotate(release_cadence=F("post_date") - F("prev_post_date"))
        .filter(release_cadence__isnull=False)
        .order_by("-release_cadence")
    )

    longest_release_chapter_to = longest_release_gap_chapters.first()
    longest_release_chapter_from = Chapter.objects.get(
        number=longest_release_chapter_to.prev_chapter_number
    )
    longest_release_gap: dt.timedelta = (
        longest_release_chapter_to.post_date - longest_release_chapter_from.post_date
    )

    context = {
        "gallery": charts.get_word_count_charts(),
        "stats": [
            HeadlineStat(
                "Total Word Count",
                f"{total_wc:,}",
                units="words",
                popup_info="The word count for each chapter is calculated by counting the tokens between spaces over the entire text. This is a simple approach, and doesn't account for any of the punctuation-related edge cases. For this reason, you may notice differences between these word counts those posted elsewhere.",
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
                    context=dict(
                        text=longest_chapter.title,
                        href=reverse("chapters", args=[longest_chapter.number]),
                        fit=True,
                    ),
                ),
                units="words",
            ),
            HeadlineStat(
                "Shortest Chapter",
                f"{shortest_chapter.word_count:,}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context=dict(
                        text=shortest_chapter.title,
                        href=reverse("chapters", args=[shortest_chapter.number]),
                        fit=True,
                    ),
                ),
                units="words",
            ),
            HeadlineStat(
                "First chapter published",
                delta_since_first_chapter_release.days,
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context=dict(
                        text=first_chapter.title,
                        href=reverse("chapters", args=[first_chapter.number]),
                        fit=True,
                    ),
                ),
                units="days ago",
            )
            if first_chapter
            else None,
            HeadlineStat(
                "Latest chapter analyzed",
                delta_since_latest_chapter_release.days,
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context=dict(
                        text=latest_chapter.title,
                        href=reverse("chapters", args=[latest_chapter.number]),
                        fit=True,
                    ),
                ),
                units="days ago",
                popup_info="This is the last chapter analyzed by the application. It is not updated after every release, so you can expect it to be a couple chapters behind the latest public release. This allows time for updates to be made to the Wiki and reduce the need for manual analysis of new chapters.",
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
                    context=dict(
                        text=longest_release_chapter_from.title,
                        href=reverse(
                            "chapters", args=[longest_release_chapter_from.number]
                        ),
                        fit=True,
                    ),
                )
                + "<div>→</div>"
                + render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context=dict(
                        text=longest_release_chapter_to.title,
                        href=reverse(
                            "chapters", args=[longest_release_chapter_to.number]
                        ),
                        fit=True,
                    ),
                ),
            ),
        ],
        "table": table,
    }
    return render(request, "pages/overview.html", context)


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
        return render(request, "tables/htmx_table.html", dict(table=table))

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
            ),
            HeadlineStat(
                "Chapter with the Most Character Mentions",
                f"{chapter_with_most_char_refs['count']}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context=dict(
                        text=chapter_with_most_char_refs["title"],
                        href=reverse(
                            "chapters", args=[chapter_with_most_char_refs.get("number")]
                        ),
                        fit=True,
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
        return render(request, "tables/htmx_table.html", dict(table=table))

    longest_class_name_by_chars = rt_data.order_by("-letter_count")[0]
    longest_class_name_by_words = rt_data.order_by("-word_count")[0]

    chapter_with_most_class_refs = (
        TextRef.objects.filter(type__type=RefType.CLASS)
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
                "Longest Class Name (by words)",
                f"{longest_class_name_by_words.word_count}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context=dict(
                        text=f"{longest_class_name_by_words.name}",
                        href=reverse(
                            "cl-stats", args=[longest_class_name_by_words.slug]
                        ),
                        fit=True,
                        no_icon=True,
                    ),
                ),
                units="words",
            ),
            HeadlineStat(
                "Longest Class Name (by letters)",
                f"{len(longest_class_name_by_chars.name)}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context=dict(
                        text=f"{longest_class_name_by_chars.name}",
                        href=reverse(
                            "cl-stats", args=[longest_class_name_by_chars.slug]
                        ),
                        fit=True,
                        no_icon=True,
                    ),
                ),
                units="letters",
                popup_info="This count includes punctuation as well as letters.",
            ),
            HeadlineStat(
                "Chapter with the Most Class Mentions",
                f"{chapter_with_most_class_refs['mentions']}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context=dict(
                        text=chapter_with_most_class_refs["title"],
                        href=reverse(
                            "chapters",
                            args=[chapter_with_most_class_refs.get("number")],
                        ),
                        fit=True,
                        no_icon=True,
                    ),
                ),
                units="[Class] mentions",
                popup_info="This count includes every instance of a mentioned [Class]. Meaning if a [Class] occurs multiple times throughout a chapter, each instance is counted.",
            ),
        ],
        "table": table,
    }

    return render(request, "pages/classes.html", context)


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
        return render(request, "tables/htmx_table.html", dict(table=table))

    longest_skill_name_by_chars = rt_data.order_by("-letter_count")[0]
    longest_skill_name_by_words = rt_data.order_by("-word_count")[0]

    chapter_with_most_skill_refs = (
        TextRef.objects.filter(type__type=RefType.SKILL)
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
                "Longest [Skill] Name (by words)",
                f"{longest_skill_name_by_words.word_count}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context=dict(
                        text=f"{longest_skill_name_by_words.name}",
                        href=reverse(
                            "sk-stats", args=[longest_skill_name_by_words.slug]
                        ),
                        fit=True,
                        no_icon=True,
                    ),
                ),
                units="words",
            ),
            HeadlineStat(
                "Longest [Skill] Name (by letters)",
                f"{len(longest_skill_name_by_chars.name)}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context=dict(
                        text=f"{longest_skill_name_by_chars.name}",
                        href=reverse(
                            "sk-stats", args=[longest_skill_name_by_chars.slug]
                        ),
                        fit=True,
                        no_icon=True,
                    ),
                ),
                units="letters",
                popup_info="This count includes punctuation as well as letters.",
            ),
            HeadlineStat(
                "Chapter with the Most [Skill] Mentions",
                f"{chapter_with_most_skill_refs['count']}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context=dict(
                        text=chapter_with_most_skill_refs["title"],
                        href=reverse(
                            "chapters", args=[chapter_with_most_skill_refs["number"]]
                        ),
                        fit=True,
                        no_icon=True,
                    ),
                ),
                units="[Skill] mentions",
                popup_info="This count includes every instance of a mentioned [Skill]. Meaning if a [Skill] occurs multiple times throughout a chapter, each instance is counted.",
            ),
        ],
        "table": table,
    }

    return render(request, "pages/skills.html", context)


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
        return render(request, "tables/htmx_table.html", dict(table=table))

    longest_spell_name_by_chars = rt_data.order_by("-letter_count")[0]
    longest_spell_name_by_words = rt_data.order_by("-word_count")[0]

    chapter_with_most_spell_refs = (
        TextRef.objects.filter(type__type=RefType.SPELL)
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
                "Longest [Spell] Name (by words)",
                f"{longest_spell_name_by_words.word_count}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context=dict(
                        text=f"{longest_spell_name_by_words.name}",
                        href=reverse(
                            "sp-stats", args=[longest_spell_name_by_words.slug]
                        ),
                        fit=True,
                        no_icon=True,
                    ),
                ),
                units="words",
            ),
            HeadlineStat(
                "Longest [Spell] Name (by letters)",
                f"{len(longest_spell_name_by_chars.name)}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context=dict(
                        text=f"{longest_spell_name_by_chars.name}",
                        href=reverse(
                            "sp-stats", args=[longest_spell_name_by_chars.slug]
                        ),
                        fit=True,
                        no_icon=True,
                    ),
                ),
                units="letters",
                popup_info="This count includes punctuation as well as letters.",
            ),
            HeadlineStat(
                "Chapter with the Most [Spell] Mentions",
                f"{chapter_with_most_spell_refs['count']}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context=dict(
                        text=chapter_with_most_spell_refs["title"],
                        href=reverse(
                            "chapters", args=[chapter_with_most_spell_refs["number"]]
                        ),
                        fit=True,
                        no_icon=True,
                    ),
                ),
                units="[Spell] mentions",
                popup_info="This count includes every instance of a mentioned [Spell]. Meaning if a [Spell] occurs multiple times throughout a chapter, each instance is counted.",
            ),
        ],
        "table": table,
    }

    return render(request, "pages/magic.html", context)


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
        return render(request, "tables/htmx_table.html", dict(table=table))

    chapter_with_most_location_refs = (
        TextRef.objects.filter(type__type=RefType.LOCATION)
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
                "Chapter with the Most Location Mentions",
                f"{chapter_with_most_location_refs['count']}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context=dict(
                        text=chapter_with_most_location_refs["title"],
                        href=reverse(
                            "chapters", args=[chapter_with_most_location_refs["number"]]
                        ),
                        fit=True,
                        no_icon=True,
                    ),
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
    except (Chapter.DoesNotExist, ValueError):
        raise Http404()

    table_filter = request.GET.get("q", "")
    table_query = dict(
        first_chapter=chapter.number, last_chapter=chapter.number, filter=table_filter
    )

    config = RequestConfig(request)
    table = get_search_result_table(table_query)
    table.hidden_cols = [1]

    config.configure(table)

    table.paginate(
        page=int(request.GET.get("page", 1)),
        per_page=request.GET.get("page_size", 25),
        orphans=5,
    )

    if request.htmx:
        return render(request, "tables/htmx_table.html", dict(table=table))

    textrefs = TextRef.objects.select_related("chapter_line__chapter", "type").filter(
        chapter_line__chapter__number=number
    )
    rt_counts = (
        textrefs.values("type")
        .annotate(count=Count("type"))
        .order_by("-count")
        .values("type__type", "type__name", "count")
    )

    most_mentioned_character = rt_counts.filter(type__type=RefType.CHARACTER).first()
    most_mentioned_class = rt_counts.filter(type__type=RefType.CLASS).first()
    most_mentioned_skill = rt_counts.filter(type__type=RefType.SKILL).first()
    most_mentioned_spell = rt_counts.filter(type__type=RefType.SPELL).first()
    most_mentioned_location = rt_counts.filter(type__type=RefType.LOCATION).first()

    context = {
        "title": chapter.title,
        "heading": render_to_string(
            "patterns/atoms/link/link.html",
            context=dict(
                text=f"Chapter {chapter.title}"
                if len(chapter.title) < 10
                else f"{chapter.title}",
                href=chapter.source_url,
                external=True,
                size=8,
            ),
        ),
        "table": table,
        "stats": [
            HeadlineStat(
                "Most mentioned character",
                f"{most_mentioned_character.get('count') if most_mentioned_character else 'None Mentioned'}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context=dict(
                        text=f"{most_mentioned_character.get('type__name')}",
                        href=reverse(
                            f'{most_mentioned_character.get("type__type").lower()}-stats',
                            args=[slugify(most_mentioned_character.get("type__name"))],
                        ),
                        fit=True,
                    ),
                ),
                units="mentions",
            )
            if most_mentioned_character
            else None,
            HeadlineStat(
                "Most mentioned class",
                f"{most_mentioned_class.get('count') if most_mentioned_class else 'None Mentioned'}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context=dict(
                        text=f"{most_mentioned_class.get('type__name')}",
                        href=reverse(
                            f'{most_mentioned_class.get("type__type").lower()}-stats',
                            args=[slugify(most_mentioned_class.get("type__name"))],
                        ),
                        fit=True,
                    ),
                ),
                units="mentions",
            )
            if most_mentioned_class
            else None,
            HeadlineStat(
                "Most mentioned skill",
                f"{most_mentioned_skill.get('count') if most_mentioned_skill else 'None Mentioned'}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context=dict(
                        text=f"{most_mentioned_skill.get('type__name')}",
                        href=reverse(
                            f'{most_mentioned_skill.get("type__type").lower()}-stats',
                            args=[slugify(most_mentioned_skill.get("type__name"))],
                        ),
                        fit=True,
                    ),
                ),
                units="mentions",
            )
            if most_mentioned_skill
            else None,
            HeadlineStat(
                "Most mentioned spell",
                f"{most_mentioned_spell.get('count') if most_mentioned_spell else 'None Mentioned'}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context=dict(
                        text=f"{most_mentioned_spell.get('type__name')}",
                        href=reverse(
                            f'{most_mentioned_spell.get("type__type").lower()}-stats',
                            args=[slugify(most_mentioned_spell.get("type__name"))],
                        ),
                        fit=True,
                    ),
                ),
                units="mentions",
            )
            if most_mentioned_spell
            else None,
            HeadlineStat(
                "Most mentioned location",
                f"{most_mentioned_location.get('count') if most_mentioned_location else 'None Mentioned'}",
                render_to_string(
                    "patterns/atoms/link/stat_link.html",
                    context=dict(
                        text=f"{most_mentioned_location.get('type__name')}",
                        href=reverse(
                            f'{most_mentioned_location.get("type__type").lower()}-stats',
                            args=[slugify(most_mentioned_location.get("type__name"))],
                        ),
                        fit=True,
                    ),
                ),
                units="mentions",
            )
            if most_mentioned_location
            else None,
        ],
        "query": table_filter,
    }
    return render(request, "pages/chapter_page.html", context)


def main_interactive_chart(request: HtmxHttpRequest, chart: str):
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
                "chart": (
                    fig.to_html(full_html=False, include_plotlyjs="cdn")
                    if fig
                    else None
                ),
                "form": form,
                "has_chapter_filter": c.has_chapter_filter,
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
                "chart": (
                    fig.to_html(full_html=False, include_plotlyjs="cdn")
                    if fig
                    else None
                ),
                "form": form,
                "has_chapter_filter": c.has_chapter_filter,
            }

            return render(request, "pages/interactive_chart.html", context)

    raise Http404()


def reftype_stats(request: HtmxHttpRequest, name: str):
    stat_root = request.path.split("/")[1].strip().lower()
    rt_type = match_reftype_str(stat_root)

    if len(name) >= 100:
        rt = RefType.objects.get(Q(slug__istartswith=name[:100]) & Q(type=rt_type))
    else:
        rt = RefType.objects.get(Q(slug__iexact=name) & Q(type=rt_type))

    # Table config and pagination
    table_query = dict(
        type=rt.type, type_query=rt.name, filter=request.GET.get("q", "")
    )

    config = RequestConfig(request)
    table = get_search_result_table(table_query)
    table.hidden_cols = [0]
    config.configure(table)
    table.paginate(
        page=int(request.GET.get("page", 1)),
        per_page=request.GET.get("page_size", 15),
        orphans=5,
    )

    if request.htmx:
        return render(request, "tables/htmx_table.html", dict(table=table))

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

    context = dict(
        table=table,
        title=rt.name,
        link=render_to_string(
            "patterns/atoms/link/link.html",
            context=dict(text="", href=href, size=8, external=True),
        ),
        aliases=aliases,
        gallery=get_reftype_gallery(rt),
        stats=(
            [
                HeadlineStat("Total mentions", mention_count, units="mentions"),
                HeadlineStat(
                    "First mentioned in chapter",
                    render_to_string(
                        "patterns/atoms/link/stat_link.html",
                        context=dict(
                            text=first_mention_chapter.chapter.title,
                            href=reverse(
                                "chapters", args=[first_mention_chapter.chapter.number]
                            ),
                            fit=True,
                            no_icon=True,
                        ),
                    ),
                ),
                HeadlineStat(
                    "Last mentioned in chapter",
                    render_to_string(
                        "patterns/atoms/link/stat_link.html",
                        context=dict(
                            text=last_mention_chapter.chapter.title,
                            href=reverse(
                                "chapters", args=[last_mention_chapter.chapter.number]
                            ),
                            fit=True,
                            no_icon=True,
                        ),
                    ),
                ),
            ]
            if first_mention_chapter and last_mention_chapter
            else None
        ),
    )
    return render(request, "pages/reftype_page.html", context)


def get_search_result_table(query: dict[str, str]) -> ChapterRefTable | TextRefTable:
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
        table_data = TextRef.objects.select_related(
            "type", "chapter_line__chapter"
        ).annotate(
            name=F("type__name"),
            text=F("chapter_line__text"),
            title=F("chapter_line__chapter__title"),
            url=F("chapter_line__chapter__source_url"),
        )

        if reftype := query.get("type"):
            table_data = table_data.filter(Q(type__type=reftype))

        if first_chapter := query.get("first_chapter"):
            table_data = table_data.filter(
                chapter_line__chapter__number__gte=first_chapter
            )

        if last_chapter := query.get("last_chapter"):
            table_data = table_data.filter(
                chapter_line__chapter__number__lte=last_chapter
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
        query["last_chapter"] = query.get("last_chapter", MAX_CHAPTER_NUM + 1)
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
            return render(request, "tables/htmx_table.html", dict(table=table))

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


def about(request: HtmxHttpRequest) -> HttpResponse:
    return render(request, "pages/about.html")
