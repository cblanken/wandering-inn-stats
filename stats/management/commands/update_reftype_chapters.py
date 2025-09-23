from django.core.management.base import BaseCommand, CommandError
from stats.models import Chapter, RefType, RefTypeChapter


class Command(BaseCommand):
    """Database build command"""

    help = "Update ReftypeChapter DB view"

    def handle(self, *_args, **_options) -> None:  # noqa: ANN002, ANN003
        new_reftypechapters = []
        for rt in RefType.objects.all():
            try:
                chapters = Chapter.objects.raw(
                    """
                    SELECT DISTINCT(cl.chapter_id) as id
                    FROM stats_textref AS tr
                        JOIN stats_chapterline AS cl ON tr.chapter_line_id = cl.id
                        JOIN stats_reftype AS rt ON rt.id = tr.type_id
                    WHERE rt.name=%s
                """,
                    [rt.name],
                )

                for chapter in chapters:
                    new_reftypechapters.append(RefTypeChapter(type=rt, chapter=chapter))

                self.stdout.write(self.style.WARNING(f"Creating RefTypeChapters for {rt.name}..."))

            except KeyboardInterrupt as exc:
                msg = "Update paused. Keyboard interrupt received."
                raise CommandError(msg) from exc

        RefTypeChapter.objects.bulk_create(new_reftypechapters, ignore_conflicts=True)
