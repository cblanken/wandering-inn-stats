"""Module for search related helper functions
Each function should return relevant table data or a full table object
"""

from django.contrib.postgres.search import SearchQuery
from django.db.models import F, Q, QuerySet
from django.http import QueryDict
from innverse.tables import ChapterRefTable, CharacterHtmxTable, TextRefTable
from stats.models import Chapter, Character, RefType, RefTypeChapter, TextRef


def get_textref_table(query: QueryDict | dict[str, str]) -> TextRefTable:
    search_filter = query.get("filter")
    strict_mode = query.get("strict_mode")
    table_data = TextRef.objects.select_related("type", "chapter_line__chapter").annotate(
        name=F("type__name"),
        text=F("chapter_line__text"),
        text_plain=F("chapter_line__text_plain"),
        title=F("chapter_line__chapter__title"),
        url=F("chapter_line__chapter__source_url"),
    )

    if (reftype := query.get("type")) is not None:
        table_data = table_data.filter(Q(type__type=reftype))

    if (first_chapter := query.get("first_chapter")) is not None:
        table_data = table_data.filter(chapter_line__chapter__number__gte=first_chapter)

    if (last_chapter := query.get("last_chapter")) is not None:
        table_data = table_data.filter(chapter_line__chapter__number__lte=last_chapter)

    if (type_query := query.get("type_query")) is not None:
        if strict_mode:
            table_data = table_data.filter(type__name=type_query)
        else:
            table_data = table_data.filter(type__name__icontains=type_query)

    if text_query := query.get("text_query"):
        table_data = table_data.filter(text_plain__search=SearchQuery(text_query, config="english"))

    if query.get("only_colored_refs"):
        table_data = table_data.filter(color__isnull=False)

    if search_filter:
        table_data = table_data.filter(
            text_plain__search=SearchQuery(search_filter, config="english", search_type="websearch")
        )

    return TextRefTable(table_data, filter_text=search_filter)


def get_chapterref_table(query: QueryDict | dict[str, str]) -> ChapterRefTable:
    strict_mode = query.get("strict_mode")
    query_filter = query.get("filter")
    if strict_mode:
        ref_types: QuerySet[RefType] = RefType.objects.filter(
            Q(name=query.get("type_query")) & Q(type=query.get("type")),
        )
    else:
        ref_types: QuerySet[RefType] = RefType.objects.filter(
            Q(name__icontains=query.get("type_query")) & Q(type=query.get("type")),
        )

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

    if query_filter:
        reftype_chapters = reftype_chapters.filter(type__name__icontains=query_filter)

    table_data = []
    for rt in ref_types:
        chapter_data = reftype_chapters.filter(type=rt).values_list("chapter__title", "chapter__source_url")

        rc_data = {
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
