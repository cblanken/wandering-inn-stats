from django.db.models import QuerySet
from stats.models import Chapter


def apply_chapter_filter(
    qs: QuerySet,
    first_chapter: Chapter | None = None,
    last_chapter: Chapter | None = None,
) -> QuerySet:
    """Filter queryset `qs` within a chapter range. Expects a column of `number`
    to check the chapter numbers within the range."""
    if first_chapter:
        qs = qs.filter(number__gte=first_chapter.number)

    if last_chapter:
        qs = qs.filter(number__lte=last_chapter.number)

    return qs
