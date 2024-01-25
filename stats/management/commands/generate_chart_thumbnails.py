from django.core.management.base import BaseCommand, CommandError
from stats import charts


class Command(BaseCommand):
    help = "Generate all chart thumbnails to static svg files"

    def add_arguments(self, parser):
        parser.add_argument(
            "--chart-name",
            type=str,
            default="",
            help="Only generate thumbnails for charts which contain the given `--chart-name`",
        )

    def handle(self, *args, **options) -> None:
        chart_galleries = [
            charts.word_count_charts,
            charts.character_charts,
            charts.class_charts,
            charts.skill_charts,
            charts.magic_charts,
        ]
        try:
            for gallery in chart_galleries:
                for chart in gallery:
                    if options.get("chart_name") in chart.title_slug:
                        fig = chart.get_fig()

                        # Remove interactive elements before export
                        fig.update_xaxes(rangeslider=dict(visible=False))

                        charts.save_thumbnail(fig, chart.path)

                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Chart ({chart.title}) saved to "{chart.path}"'
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f'Chart ({chart.title}) did not match chart-name: "{options.get("chart_name")}"'
                            )
                        )
        except KeyboardInterrupt as exc:
            raise CommandError(
                "Keyboard interrupt...thumbnail generation stopped."
            ) from exc
