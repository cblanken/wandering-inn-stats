from math import inf
from time import sleep
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from requests import codes as status_codes
from processing import get

class Command(BaseCommand):
    help = "Download Wandering Inn chapters by volume"
    VOLUMES_PATH = Path("./volumes")
    VOLUMES_PATH.mkdir(exist_ok=True)
    REQUEST_DELAY_SEC = 2.0

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

            if toc.response.status_code != status_codes["ok"]:
                raise CommandError(f"The table of contents ({toc.url}) could not be downloaded.\nCheck your network connection and confirm the host hasn't been IP blocked.")
            start = options.get("first_volume")
            end = start + options.get("range")

            # Create volume / book / chapter directory structure
            for i, (volume_title, books) in list(enumerate(toc.volume_data.items()))[start:end]:
                if i >= options.get("first_volume") + options.get("range"):
                    break
                volume_path = Path(self.VOLUMES_PATH, f"{i:0>2}_{volume_title}")
                volume_path.mkdir(exist_ok=True)
                for j, (book_title, chapters) in enumerate(books.items()):
                    book_path = Path(volume_path, f"{j:>02}_{book_title}")
                    book_path.mkdir(exist_ok=True)

                    for k, (chapter_title, chapter_href) in enumerate(chapters.items()):
                        src_path = Path(book_path, f"{k:>03}_{chapter_title}.html")
                        txt_path = Path(book_path, f"{k:>03}_{chapter_title}.txt")

                        # Download chapter
                        self.stdout.write(f"Downloading {chapter_href}")
                        chapter_response = get.get_chapter(chapter_href)
                        if chapter_response is None:
                            raise CommandError(f"Could not get chapter at {chapter_href}")

                        html = get.get_chapter_html(chapter_response)
                        text = get.get_chapter_text(chapter_response)

                        get.save_file(src_path, html)
                        self.stdout.write("> ", ending="")
                        self.stdout.write(
                            self.style.SUCCESS(f"\"{chapter_title}\" html saved to {src_path}")
                        )

                        get.save_file(txt_path, text)
                        self.stdout.write("> ", ending="")
                        self.stdout.write(
                            self.style.SUCCESS(f"\"{chapter_title}\" text saved to {txt_path}")
                        )

                    sleep(self.REQUEST_DELAY_SEC)
        except KeyboardInterrupt as exc:
            # TODO: file / partial download cleanup
            raise CommandError("\nKeyboard interrupt...downloads stopped") from exc

        # TODO add pause/resume
        # TODO add type hinting
        # TODO add chapter hashing to check for changes
        # TODO add chapter archiving functionality
        # TODO use urllib or requests to handle URLs
        # TODO add error handling
        # TODO add jitter to download loop
