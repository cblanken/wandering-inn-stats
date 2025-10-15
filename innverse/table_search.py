"""Module for search related helper functions
Each function should return relevant table data or a full table object
"""

from typing import Any

from django.contrib.postgres.search import SearchHeadline, SearchQuery
from django.db.models import F, Q, QuerySet
from django.http import QueryDict

from innverse.tables import ChapterLineTable, ChapterRefTable, CharacterHtmxTable, TextRefTable
from stats.models import Chapter, ChapterLine, Character, RefType, RefTypeChapter, TextRef


def get_chapterline_table(query: dict[str, Any]) -> ChapterLineTable:
    table_data = ChapterLine.objects.all()

    # Handle chapter range filtering
    if (first_chapter := query.get("first_chapter")) is not None:
        table_data = table_data.filter(chapter__number__gte=first_chapter)

    if (last_chapter := query.get("last_chapter")) is not None:
        table_data = table_data.filter(chapter__number__lte=last_chapter)

    # Handle full-text search filtering
    if search_filter := query.get("q"):
        config = "english_nostop" if '"' in search_filter else "english"
        search_query = SearchQuery(search_filter, config=config, search_type="websearch")

        full_text_search_data = table_data.filter(text_plain__search=search_query).annotate(
            headline=SearchHeadline(
                "text_plain",
                search_query,
                config=config,
                start_sel="<span class='text-black bg-hl-tertiary'>",
                stop_sel="</span>",
                highlight_all=True,
            )
        )

        # Fallback to basic icontains search if the SearchQuery fails, for example,
        # if the query only contains stop words
        if not full_text_search_data:
            search_filter = search_filter.replace('"', "")
            table_data = table_data.filter(text_plain__icontains=search_filter)
        else:
            table_data = full_text_search_data

    return ChapterLineTable(table_data)


def get_textref_table(query: dict[str, Any]) -> TextRefTable:
    # Handle TextRef reftype filtering
    table_data = TextRef.objects.select_related("type", "chapter_line").annotate(
        name=F("type__name"),
        text=F("chapter_line__text"),
        text_plain=F("chapter_line__text_plain"),
        title=F("chapter_line__chapter__title"),
        source_url=F("chapter_line__chapter__source_url"),
        number=F("chapter_line__chapter__number"),
    )

    if reftype := query.get("type"):
        table_data = table_data.filter(Q(type__type=reftype))

    if type_query := query.get("type_query"):
        table_data = table_data.filter(type__name__icontains=type_query)
    if query.get("only_colored_refs"):
        table_data = table_data.filter(color__isnull=False)

    # Handle chapter range filtering
    if (first_chapter := query.get("first_chapter")) is not None:
        table_data = table_data.filter(number__gte=first_chapter)

    if (last_chapter := query.get("last_chapter")) is not None:
        table_data = table_data.filter(number__lte=last_chapter)

    # Handle full-text search filtering
    if search_filter := query.get("q"):
        config = "english_nostop" if '"' in search_filter else "english"
        search_query = SearchQuery(search_filter, config=config, search_type="websearch")

        full_text_search_data = table_data.filter(text_plain__search=search_query).annotate(
            headline=SearchHeadline(
                "text_plain",
                search_query,
                config=config,
                start_sel="<span class='text-black bg-hl-tertiary'>",
                stop_sel="</span>",
                highlight_all=True,
            )
        )

        # Fallback to basic icontains search if the SearchQuery fails, for example,
        # if the query only contains stop words
        if not full_text_search_data:
            search_filter = search_filter.replace('"', "")
            table_data = table_data.filter(text_plain__icontains=search_filter)
        else:
            table_data = full_text_search_data

    return TextRefTable(table_data, filter_text=search_filter)


def get_chapterref_table(query: QueryDict | dict[str, str]) -> ChapterRefTable:
    reftype = query.get("type", "")
    type_query = query.get("type_query", "")

    ref_types: QuerySet[RefType] = RefType.objects.all()
    if reftype != "":
        ref_types = RefType.objects.filter(Q(type=reftype))
    if type_query != "":
        ref_types = RefType.objects.filter(Q(name__icontains=type_query))

    reftype_chapters = RefTypeChapter.objects.filter(
        Q(type__in=ref_types)
        & Q(chapter__number__gte=query.get("first_chapter"))
        & Q(
            chapter__number__lte=query.get(
                "last_chapter",
                int(Chapter.objects.values_list("number").order_by("-number")[0][0]),
            ),
        ),
    )

    table_data = []
    for rt in ref_types:
        chapter_data = reftype_chapters.filter(type=rt).values_list("chapter__title", "chapter__source_url")

        rc_data: dict[str, Any] = {
            "name": rt.name,
            "type": rt.type,
            "chapter_data": chapter_data,
        }

        rc_data["count"] = len(rc_data["chapter_data"])

        if rc_data["chapter_data"]:
            table_data.append(rc_data)

    return ChapterRefTable(table_data)


def get_character_table(query: QueryDict) -> CharacterHtmxTable:
    data = (
        Character.objects.select_related("ref_type", "ref_type__reftypecomputedview", "first_chapter_appearance")
        .annotate(
            mentions=F("ref_type__reftypecomputedview__mentions"),
            first_mention_num=F("ref_type__reftypecomputedview__first_mention__number"),
            first_mention_title=F("ref_type__reftypecomputedview__first_mention__title"),
        )
        .order_by(F("mentions").desc(nulls_last=True))
    )
    if q := query.get("q"):
        filter_expression = Q(ref_type__name__icontains=q) | Q(first_chapter_appearance__title__icontains=q)

        if (species := Character.identify_species(q)) != Character.Species.UNKNOWN.value.shortcode:
            filter_expression = filter_expression | Q(species=species)

        if (status := Character.identify_status(q)) != Character.Status.UNKNOWN.value.shortcode:
            filter_expression = filter_expression | Q(status=status)

        data = data.filter(filter_expression)

    return CharacterHtmxTable(data)


def get_reftype_table_data(query: str | None, rt_type: str, order_by: str = "mentions") -> QuerySet[RefType]:
    rt_data = (
        RefType.objects.select_related("reftypecomputedview")
        .annotate(
            mentions=F("reftypecomputedview__mentions"),
            first_mention_num=F("reftypecomputedview__first_mention__number"),
            first_mention_title=F("reftypecomputedview__first_mention__title"),
        )
        .order_by(F(order_by).desc(nulls_last=True))
    )

    return rt_data.filter(type=rt_type, name__icontains=query) if query else rt_data.filter(type=rt_type)
