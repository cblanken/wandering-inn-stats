from math import inf
from time import sleep
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from processing import get

class Command(BaseCommand):
    help = "Download Wandering Inn chapters by volume"
    VOLUMES_PATH = Path("./volumes")
    VOLUMES_PATH.mkdir(exist_ok=True)
    REQUEST_DELAY_SEC = 1.0

    def add_arguments(self, parser):
        parser.add_argument("first_volume", nargs="?", type=int, default=0,
                             help="Index of starting volume to download")
        parser.add_argument("range", nargs="?", type=int,  default=inf,
                             help="How many volumes to download starting with `first_volume`")
        parser.add_argument("request_delay", nargs="?", default=1.0,
                            help="Time delay")

    def handle(self, *args, **options):
        # TODO: add option to diff previous table of contents to check for changes and
        # only get the latest posted volumes/chapters
        try:
            toc = get.TableOfContents()
            volumes = toc.get_volume_data()

            start = options.get("first_volume")
            for i, volume in enumerate(volumes[start:], start=start):
                volume_path = Path(self.VOLUMES_PATH, volume[0])
                volume_path.mkdir(exist_ok=True)
                for j, link in enumerate(volume[1]):

                    if i >= options.get("first_volume") + options.get("range"):
                        break
                    
                    chapter_path = Path(volume_path, str(j))
                    chapter_path.mkdir(exist_ok=True)

                    # remove trailing '/' from URL and replace '/' with '-'
                    chapter_title = link.text.strip()
                    chapter_href = link['href']

                    filename = f"{chapter_title}"

                    src_path = Path(chapter_path, filename + ".html")
                    txt_path = Path(chapter_path, filename + ".txt")

                    # TODO: add clobber/no-clobber toggle option
                    # Skip already downloaded chapters
                    #if src_path.exists() or txt_path.exists():
                    #    continue
                    chapter_response = get.get_chapter(chapter_href)
                    if chapter_response is None:
                        raise CommandError(f"Could not get chapter at {chapter_href}")

                    html = chapter_response.text
                    text = get.get_chapter_text(chapter_response)

                    self.stdout.write(f"{j}: Downloading {chapter_href}")
                    get.save_file(src_path, html)
                    self.stdout.write(
                        self.style.SUCCESS(f" > {chapter_href} html saved to {src_path}")
                    )

                    get.save_file(txt_path, text)
                    self.stdout.write(
                        self.style.SUCCESS(f" > {chapter_href} text saved to {txt_path}")
                    )

                    sleep(self.REQUEST_DELAY_SEC)
        except KeyboardInterrupt as exc:
            # TODO: file / partial download cleanup
            raise CommandError("Keyboard interrupt...downloads stopped") from exc

        # TODO add pause/resume
        # TODO add type hinting
        # TODO add chapter hashing to check for changes
        # TODO add chapter archiving functionality
        # TODO use urllib or requests to handle URLs
        # TODO add error handling
        # TODO add jitter to download loop
