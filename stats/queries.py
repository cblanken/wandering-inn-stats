from stats.models import Chapter, Character, RefType, RefTypeChapter, TextRef
from django.db.models import Count, F, Q, QuerySet, Sum, Func, Value, IntegerField


def annotate_reftype_lengths(qs: QuerySet[RefType]) -> QuerySet:
    return (
        qs.annotate(
            words=Func(F("name"), Value(r"\s+"), function="regexp_split_to_array")
        )
        .annotate(
            word_count=Func(
                F("words"), 1, function="array_length", output_field=IntegerField()
            )
        )
        .annotate(len=F("name__length"))
    )


def get_reftype_mentions(rt_type: str) -> QuerySet:
    return (
        TextRef.objects.filter(type__type=rt_type)
        .select_related("type", "chapter_line__chapter")
        .values("type__name")
        .annotate(name=F("type__name"))
        .annotate(mentions=Count("type__name"))
        .annotate(
            words=Func(F("name"), Value(r"\s+"), function="regexp_split_to_array")
        )
        .annotate(
            word_count=Func(
                "words", 1, function="array_length", output_field=IntegerField()
            )
        )
        .annotate(letter_count=F("name__length"))
    )
