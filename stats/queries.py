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
