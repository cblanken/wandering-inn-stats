"""Download command for wanderinginn.com"""
import json
from pathlib import Path
import time
from django.core.management.base import BaseCommand, CommandError
from requests import codes as status_codes
from processing import get

class Command(BaseCommand):
    help = "Download Wandering Inn chapters by volume"
    last_download: float = 0.0

    def add_arguments(self, parser):
        parser.add_argument("volume", nargs="?", type=str,
                            help="Volume to download")
        parser.add_argument("book", nargs="?", type=str,
                            help="Book to download")
        parser.add_argument("chapter", nargs="?", type=str,
                            help="Chapter to download")
        parser.add_argument("-a", "--all", action="store_true",
                            help="Download all volumes")
        parser.add_argument("-i", "--index", action="store_true",
                            help="Retrieve volume/book/chapter by indexes instead of title")
        parser.add_argument("-d", "--request_delay", default=2.0,
                            help="Time delay")
        parser.add_argument("-r", "--root", default="./volumes",
                            help="Root path of volumes to save to")
        parser.add_argument("-c", "--clobber", action="store_true",
                            help="Overwrite chapter files if they already exist")
        parser.add_argument("-l", "--latest", action="store_true",
                            help="Download only the most recently released chapter")

    def handle(self, *args, **options):
        tor_session = get.TorSession()
        self.stdout.write("Connecting to Tor session...")
        toc = get.TableOfContents(tor_session)
        self.last_download: int = 0

        def save_file(text: str, path: Path, success_msg: str = None, warn_msg: str = None):
            was_saved = get.save_file(path, text, clobber=options.get("clobber"))

            if was_saved:
                if success_msg is None:
                    success_msg = f"\"{path}\" saved"
                self.stdout.write("> ", ending="")
                self.stdout.write(self.style.SUCCESS(success_msg))
            else:
                if warn_msg is None:
                    warn_msg = f"\"{path}\" could not be saved"
                self.stdout.write("> ", ending="")
                self.stdout.write(self.style.WARNING(warn_msg))
            
            return was_saved

        def download_last_chapter():
            # TODO
            pass

        def download_chapter(volume_title: str, book_title: str, chapter_title: str, chapter_path: Path):
            try:
                chapter_href = toc.volume_data[volume_title][book_title][chapter_title]
            except KeyError as exc:
                self.stdout.write(self.style.WARNING(f"Could not find {exc}"))
                return

            # Throttle chapter downloads
            while time.time() < self.last_download + options.get("request_delay"):
                time.sleep(0.1)

            # Download chapter
            chapter_path.mkdir(parents=True, exist_ok=True)
            src_path = Path(chapter_path, f"{chapter_title}.html")
            txt_path = Path(chapter_path, f"{chapter_title}.txt")
            meta_path = Path(chapter_path, f"metadata.json")

            if not options.get("clobber") and src_path.exists() and txt_path.exists() and meta_path.exists():
                self.stdout.write(self.style.NOTICE(f"> All chapter files exist for chapter: \"{chapter_title}\". Skipping..."))
                return

            self.stdout.write(f"Downloading {chapter_href}")
            chapter_response = tor_session.get_chapter(chapter_href)
            if chapter_response is None:
                self.stdout.write(self.style.WARNING("! Chapter could not be downloaded!"))
                self.stdout.write(f"Skipping download for {chapter_title} → {chapter_href}")
                tor_session.reset_tries()
                return

            html: str = get.get_chapter_html(chapter_response)
            text: str = get.get_chapter_text(chapter_response)
            metadata: dict = get.get_chapter_metadata(chapter_response)

            if html is None or text is None or metadata is None:
                self.stdout.write(self.style.WARNING("Some data could not be parsed from:"))
                self.stdout.write(f"HTTP Response:\n {chapter_response}")
                self.stdout.write(f"Skipping download for {chapter_title} → {chapter_href}")
                return

            # Save source HTML
            save_file(
                text = html,
                path = src_path,
                success_msg = f"\"{chapter_title}\" html saved to {src_path}",
                warn_msg = f"{src_path} already exists. Not saving...")

            # Save text
            save_file(
                text = text,
                path = txt_path,
                success_msg = f"\"{chapter_title}\" text saved to {txt_path}",
                warn_msg = f"{txt_path} already exists. Not saving...")

            # Save metadata
            save_file(
                text = json.dumps(metadata, sort_keys=True, indent=4),
                path = meta_path,
                success_msg = f"\"{chapter_title}\" metadata saved to {meta_path}",
                warn_msg = f"{meta_path} already exists. Not saving...")

            self.last_download = time.time()

        def download_book(volume_title: str, book_title: str, book_path: Path):
            book_path.mkdir(parents=True, exist_ok=True)
            chapters = toc.volume_data[volume_title][book_title]
            
            # Save metadata
            metadata: dict = {
                "title": book_title,
                "chapters": { k:i for (i, (k,_)) in enumerate(chapters.items()) }
            }
            meta_path = Path(book_path, "metadata.json")
            save_file(
                text = json.dumps(metadata, sort_keys=True, indent=4),
                path = meta_path,
                success_msg = f"\"{book_title}\" metadata saved to {meta_path}",
                warn_msg = f"{meta_path} already exists. Not saving...")

            for chapter_title in chapters:
                chapter_path = Path(book_path, chapter_title)
                download_chapter(volume_title, book_title, chapter_title, chapter_path)

        def download_volume(volume_title: str, volume_path: Path):
            volume_path.mkdir(parents=True, exist_ok=True)
            books = toc.volume_data[volume_title]

            # Save metadata
            metadata: dict = {
                "title": volume_title,
                "books": { k:i for (i, (k,_)) in enumerate(books.items()) }
            }
            meta_path = Path(volume_path, "metadata.json")
            save_file(
                text = json.dumps(metadata, sort_keys=True, indent=4),
                path = meta_path,
                success_msg = f"\"{volume_title}\" metadata saved to {meta_path}",
                warn_msg = f"{meta_path} already exists. Not saving...")

            for book_title in books:
                book_path = Path(volume_path, book_title)
                download_book(volume_title, book_title, book_path)

        # TODO: add option to diff previous table of contents to check for changes and
        # only get the latest posted volumes/chapters
        try:
            if toc.response is None:
                raise CommandError(f"The table of contents ({toc.url}) could not be downloaded.\nCheck your network connection and confirm the host hasn't been IP blocked.")

            #start = options.get("first_volume")
            #end = start + options.get("range")
            v_title = options.get("volume")
            b_title = options.get("book")
            c_title = options.get("chapter")

            volume_root = Path(options.get("root"))
            volume_root.mkdir(exist_ok=True)
          
            if options.get("all"):
                # Save metadata
                metadata: dict = {
                    "title": "The Wandering Inn",
                    "volumes": { k:i for i, k in enumerate(toc.volume_data) }
                }
                meta_path = Path(volume_root, "metadata.json")
                save_file(
                    text = json.dumps(metadata, sort_keys=True, indent=4),
                    path = meta_path,
                    success_msg = f"Volumes metadata saved to {meta_path}",
                    warn_msg = f"{meta_path} already exists. Not saving...")

                # Download all volumes
                for i, (volume_title, books) in list(enumerate(toc.volume_data.items())):
                    volume_path = Path(volume_root, f"{volume_title}")
                    download_volume(volume_title, volume_path)
            elif options.get("chapter"):
                # Download selected chapter
                path = Path(volume_root, v_title, b_title, c_title)
                download_chapter(v_title, b_title, c_title, path)
            elif options.get("book"):
                # Download selected book
                path = Path(volume_root, v_title, b_title)
                download_book(v_title, b_title, path)
            elif options.get("volume"):
                # Download selected volume
                path = Path(volume_root, v_title)
                download_volume(v_title, path)
        except KeyboardInterrupt as exc:
            # TODO: file / partial download cleanup
            raise CommandError("Keyboard interrupt...downloads stopped") from exc

        # TODO add pause/resume
        # TODO add type hinting
        # TODO add chapter hashing to check for changes
        # TODO add chapter archiving functionality
        # TODO use urllib or requests to handle URLs
        # TODO add error handling
