import json
from math import inf
from time import sleep
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from requests import codes as status_codes
from processing import get

#def download_chapter(root: Path, volume: str, book: str, chapter: str):
#    path = Path(root, )
#    was_saved = get.save_file(txt_path, text, clobber=options.get("clobber"))
#
#def download_last_chapter():
#    pass

class Command(BaseCommand):
    help = "Download Wandering Inn chapters by volume"
    toc = get.TableOfContents()

    def add_arguments(self, parser):
        parser.add_argument("first_volume", nargs="?", type=int, default=0,
                             help="Index of starting volume to download")
        parser.add_argument("range", nargs="?", type=int,  default=inf,
                             help="How many volumes to download starting with `first_volume`")
        parser.add_argument("request_delay", nargs="?", default=2.0,
                            help="Time delay")
        parser.add_argument("-r", "--root", default="./volumes",
                            help="Root path of volumes")
        parser.add_argument("-c", "--clobber", action="store_true",
                            help="Overwrite chapter files if they already exist")

    def handle(self, *args, **options):
        # TODO: add option to diff previous table of contents to check for changes and
        # only get the latest posted volumes/chapters
        try:
            if self.toc.response.status_code != status_codes["ok"]:
                raise CommandError(f"The table of contents ({self.toc.url}) could not be downloaded.\nCheck your network connection and confirm the host hasn't been IP blocked.")
            start = options.get("first_volume")
            end = start + options.get("range")

            # Create volume / book / chapter directory structure
            for i, (volume_title, books) in list(enumerate(self.toc.volume_data.items()))[start:end]:
                if i >= options.get("first_volume") + options.get("range"):
                    break
                volume_path = Path(options.get("root"), f"{i:0>2}_{volume_title}")
                volume_path.mkdir(exist_ok=True)
                for j, (book_title, chapters) in enumerate(books.items()):
                    book_path = Path(volume_path, f"{j:>02}_{book_title}")
                    book_path.mkdir(exist_ok=True)

                    for k, (chapter_title, chapter_href) in enumerate(chapters.items()):
                        src_path = Path(book_path, f"{k:>03}_{chapter_title}.html")
                        txt_path = Path(book_path, f"{k:>03}_{chapter_title}.txt")
                        meta_path = Path(book_path, f"{k:>03}_{chapter_title}.json")

                        # Download chapter
                        self.stdout.write(f"Downloading {chapter_href}")
                        chapter_response = get.get_chapter(chapter_href)
                        if chapter_response is None:
                            raise CommandError(f"Could not get chapter at {chapter_href}")

                        html = get.get_chapter_html(chapter_response)
                        text = get.get_chapter_text(chapter_response)
                        meta = get.get_chapter_metadata(chapter_response)

                        # Save HTML
                        was_saved = get.save_file(src_path, html, clobber=options.get("clobber"))
                        if was_saved:
                            self.stdout.write("> ", ending="")
                            self.stdout.write(self.style.SUCCESS(f"\"{chapter_title}\" html saved to {src_path}"))
                        else:
                            self.stdout.write("> ", ending="")
                            self.stdout.write(self.style.WARNING(f"{src_path} already exists. Not saving..."))

                        # Save text
                        was_saved = get.save_file(txt_path, text, clobber=options.get("clobber"))
                        if was_saved:
                            self.stdout.write("> ", ending="")
                            self.stdout.write(self.style.SUCCESS(f"\"{chapter_title}\" text saved to {txt_path}"))
                        else:
                            self.stdout.write("> ", ending="")
                            self.stdout.write(self.style.WARNING(f"{txt_path} already exists. Not saving..."))

                        # Save metadata
                        was_saved = get.save_file(meta_path, json.dumps(meta), clobber=options.get("clobber"))
                        if was_saved:
                            self.stdout.write("> ", ending="")
                            self.stdout.write(self.style.SUCCESS(f"\"{chapter_title}\" metadata saved to {meta_path}"))
                        else:
                            self.stdout.write("> ", ending="")
                            self.stdout.write(self.style.WARNING(f"{meta_path} already exists. Not saving..."))

                        sleep(options.get("request_delay"))
        except KeyboardInterrupt as exc:
            # TODO: file / partial download cleanup
            raise CommandError("Keyboard interrupt...downloads stopped") from exc

        # TODO add pause/resume
        # TODO add type hinting
        # TODO add chapter hashing to check for changes
        # TODO add chapter archiving functionality
        # TODO use urllib or requests to handle URLs
        # TODO add error handling
