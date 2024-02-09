from django.contrib.postgres.fields import ArrayField
from django.db.models import (
    Count,
    F,
    Q,
    QuerySet,
    Sum,
    Func,
    Value,
    TextField,
    IntegerField,
)

from stats.models import TextRef


def get_reftype_mentions(rt_type: str) -> QuerySet:
    return (
        TextRef.objects.filter(type__type=rt_type)
        .select_related("type", "chapter_line__chapter")
        .values("type__name")
        .annotate(name=F("type__name"))
        .annotate(mentions=Count("type__name"))
        .annotate(
            words=Func(
                F("name"),
                Value(r"\s+"),
                function="regexp_split_to_array",
                output_field=ArrayField(TextField()),
            )
        )
        .annotate(
            word_count=Func(
                "words", 1, function="array_length", output_field=IntegerField()
            )
        )
        .annotate(
            letter_count=Func(
                "name", arity=1, function="length", output_field=IntegerField()
            )
        )
    )
