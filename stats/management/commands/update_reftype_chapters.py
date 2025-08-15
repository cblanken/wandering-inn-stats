from django.core.management.base import BaseCommand, CommandError
from django.db.models import F, Subquery
from stats.models import Chapter, TextRef, RefType, RefTypeChapter


class Command(BaseCommand):
    """Database build command"""

    help = "Update database from chapter source HTML and other metadata files"

    def handle(self, *_args, **_options) -> None:  # noqa: ANN002, ANN003
        for rt in RefType.objects.all():
            textref_query = (
                TextRef.objects.filter(type=rt)
                .annotate(chapter_id=F("chapter_line__chapter__id"))
                .order_by("chapter_id")
                .distinct("chapter_id")
                .values("chapter_id")
                .all()
            )
            try:
                for c in Chapter.objects.filter(id__in=Subquery(textref_query)):
                    (
                        ref_type_chapter,
                        ref_type_chapter_created,
                    ) = RefTypeChapter.objects.get_or_create(type=rt, chapter=c)
                    if ref_type_chapter_created:
                        self.stdout.write(self.style.SUCCESS(f"Created RefTypeChapter for {rt.name} - {c.title}"))
                    else:
                        self.stdout.write(
                            self.style.WARNING(f"RefTypeChapter for {rt.name} - {c.title} already exists."),
                        )

            except KeyboardInterrupt as exc:
                raise CommandError("Update paused. Keyboard interrupt received.") from exc
