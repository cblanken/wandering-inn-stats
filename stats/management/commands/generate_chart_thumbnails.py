from django.core.management.base import BaseCommand, CommandError
from stats import charts
from stats.models import RefType


class Command(BaseCommand):
    help = "Generate chart thumbnails to static svg files"

    def add_arguments(self, parser):
        parser.add_argument(
            "-n",
            "--chart-name",
            type=str,
            default="",
            help="Only generate thumbnails for charts which contain the given `--chart-name`",
        )
        parser.add_argument(
            "-c",
            "--clobber",
            action="store_true",
            help="Clobber existing thumbnail files",
        )

        parser.add_argument(
            "--reftypes-only",
            action="store_true",
            help="Only generate thumbnails for reftype charts",
        )

    def save_chart_thumbnail(self, options, chart: charts.ChartGalleryItem):
        if options.get("chart_name") in str(chart.title):
            fig = chart.get_fig()

            # Remove interactive elements before export
            fig.update_xaxes(rangeslider=dict(visible=False))
            fig.update_layout(title=dict(text=""))

            charts.save_thumbnail(fig, chart.path)

            self.stdout.write(
                self.style.SUCCESS(f'> Chart ({chart.title}) saved to "{chart.path}"')
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'> Chart ({chart.title}) did not match chart-name: "{options.get("chart_name")}"'
                )
            )

    def handle(self, *args, **options) -> None:
        main_chart_galleries = [
            charts.word_count_charts,
            charts.character_charts,
            charts.class_charts,
            charts.skill_charts,
            charts.magic_charts,
            charts.location_charts,
        ]
        try:
            if not options.get("reftypes_only"):
                for gallery in main_chart_galleries:
                    for chart in gallery:
                        if options.get("clobber") or not chart.path.exists():
                            self.save_chart_thumbnail(options, chart)
                        else:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"> Thumbnail for {chart.title} already exists at {chart.static_path}"
                                )
                            )

            for rt in RefType.objects.filter(name__icontains=options.get("chart_name")):
                print(f"> Generating gallery for: {rt.name}")
                gallery = charts.get_reftype_gallery(rt)
                for chart in gallery:
                    if not chart.path.exists() or options.get("clobber"):
                        self.save_chart_thumbnail(options, chart)
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"> Thumbnail for {rt.name} already exists at {chart.static_path}"
                            )
                        )

        except KeyboardInterrupt as exc:
            raise CommandError(
                "Keyboard interrupt...thumbnail generation stopped."
            ) from exc
