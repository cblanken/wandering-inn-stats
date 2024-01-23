from django.core.management.base import BaseCommand, CommandError
from stats import charts


class Command(BaseCommand):
    help = "Generate all chart thumbnails to static svg files"

    def handle(self, *args, **options) -> None:
        chart_galleries = [
            charts.word_count_charts,
            charts.character_charts,
            charts.class_charts,
        ]
        try:
            for gallery in chart_galleries:
                for chart in gallery:
                    chart.save_thumbnail()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Chart ({chart.title}) saved to "{chart.path}"'
                        )
                    )
        except KeyboardInterrupt as exc:
            raise CommandError(
                "Keyboard interrupt...thumbnail generation stopped."
            ) from exc
