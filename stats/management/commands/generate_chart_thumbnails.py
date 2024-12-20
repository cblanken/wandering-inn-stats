from django.core.management.base import BaseCommand, CommandError
from stats import charts
from stats.models import RefType
import re

import cProfile
import pstats
import io


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

        parser.add_argument(
            "-t", "--reftype-name", help="Specify regex for RefType name"
        )

    def save_chart_thumbnail(self, options, chart: charts.ChartGalleryItem):
        if options.get("chart_name") in str(chart.title):
            fig = chart.get_fig()

            if fig:
                # Remove interactive elements before export
                fig.update_xaxes(rangeslider=dict(visible=False))
                fig.update_layout(title=dict(text=""), showlegend=False)

                chart.path.parent.mkdir(parents=True, exist_ok=True)
                fig.write_image(file=chart.path, format="svg")

                self.stdout.write(
                    self.style.SUCCESS(
                        f'> Chart ({chart.title}) saved to "{chart.path}"'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"> Chart ({chart.title}) did not have enough data. Skipped."
                    )
                )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'> Chart ({chart.title}) did not match chart-name: "{options.get("chart_name")}"'
                )
            )

    def handle(self, *args, **options) -> None:
        pr = cProfile.Profile()
        pr.enable()

        main_chart_galleries = [
            charts.get_word_count_charts(),
            charts.get_character_charts(),
            charts.get_class_charts(),
            charts.get_skill_charts(),
            charts.get_magic_charts(),
            charts.get_location_charts(),
        ]
        if reftype_name := options.get("reftype_name", None):
            pattern = re.compile(reftype_name)
        else:
            pattern = None
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
                if pattern and not pattern.match(rt.name):
                    continue

                print(f"> Generating gallery for: {rt.name}")
                gallery = charts.get_reftype_gallery(rt)
                for chart in gallery:
                    if options.get("clobber") or not chart.path.exists():
                        self.save_chart_thumbnail(options, chart)
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"> Thumbnail for {rt.name} already exists at {chart.static_path}"
                            )
                        )

        except KeyboardInterrupt as exc:
            s = io.StringIO()
            ps = pstats.Stats(pr, stream=s).sort_stats(pstats.SortKey.CUMULATIVE)
            ps.print_stats(25)
            print(s.getvalue())

            raise CommandError(
                "Keyboard interrupt...thumbnail generation stopped."
            ) from exc
