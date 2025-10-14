"""Download command for wanderinginn.com"""

import json
import time
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from processing import get
from processing.exceptions import PatreonChapterError


class Command(BaseCommand):
    help = "Download Wandering Inn source text and metadata including volumes, books, chapters"
    last_download: float = 0

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("volume", nargs="?", type=str, help="Volume to download")
        parser.add_argument("book", nargs="?", type=str, help="Book to download")
        parser.add_argument("chapter", nargs="?", type=str, help="Chapter to download")
        parser.add_argument("-a", "--all", action="store_true", help="Download all volumes")
        parser.add_argument(
            "-i",
            "--index",
            action="store_true",
            help="Retrieve volume/book/chapter by indexes instead of title",
        )
        parser.add_argument("-t", "--throttle", default=3.0, help="Time delay between requests")
        parser.add_argument("-r", "--root", default="./data", help="Root path of downloaded data")
        parser.add_argument(
            "--volume_root",
            default="volumes",
            help="Path under root directory to save volumes",
        )
        parser.add_argument(
            "-c",
            "--clobber",
            action="store_true",
            help="Overwrite chapter files if they already exist",
        )
        parser.add_argument(
            "-l",
            "--latest",
            action="store_true",
            help="Download only the most recently released chapter",
        )
        parser.add_argument("-m", "--metadata-only", action="store_true", help="Download only metadata")

    def save_file(
        self,
        text: str,
        path: Path,
        clobber: bool,
        success_msg: str = "",
        warn_msg: str = "",
    ) -> bool:
        was_saved = get.save_file(path, text, clobber=clobber)

        if was_saved:
            if success_msg == "":
                success_msg = f'"{path}" saved'
            self.stdout.write("> ", ending="")
            self.stdout.write(self.style.SUCCESS(success_msg))
        else:
            if warn_msg is None:
                warn_msg = f'"{path}" could not be saved'
            self.stdout.write("> ", ending="")
            self.stdout.write(self.style.WARNING(warn_msg))

        return was_saved

    def download_chapter(
        self,
        toc: get.TableOfContents,
        options: dict[str, Any],
        volume_title: str,
        book_title: str,
        chapter_title: str,
        chapter_path: Path,
    ) -> None:
        try:
            chapter_href = toc.volume_data[volume_title][book_title][chapter_title]
        except KeyError as exc:
            self.stdout.write(self.style.WARNING(f"Could not find {exc}"))
            return

        # Download chapter
        chapter_path.mkdir(parents=True, exist_ok=True)
        src_path = Path(chapter_path, f"{chapter_title}.html")
        cleaned_src_path = Path(chapter_path, f"{chapter_title}_cleaned.html")
        txt_path = Path(chapter_path, f"{chapter_title}.txt")
        authors_note_path = Path(chapter_path, f"{chapter_title}_authors_note.txt")
        meta_path = Path(chapter_path, "metadata.json")

        if not options.get("clobber") and src_path.exists() and txt_path.exists() and meta_path.exists():
            self.stdout.write(
                self.style.NOTICE(f'> All chapter files exist for chapter: "{chapter_title}". Skipping...'),
            )
            return

        self.stdout.write(f"Downloading {chapter_href}")
        chapter_response = self.session.get(chapter_href)
        if chapter_response is None:
            self.stdout.write(self.style.WARNING("! Chapter could not be downloaded!"))
            self.stdout.write(f"Skipping download for {chapter_title} → {chapter_href}")
            self.session.reset_tries()
            return

        try:
            data = get.parse_chapter_response(chapter_response)
        except PatreonChapterError:
            self.stdout.write(
                self.style.WARNING(f"Patreon locked chapter detected. Skipping download for {chapter_title}"),
            )
            return

        if data.get("html") is None or data.get("text") is None or data.get("metadata") is None:
            self.stdout.write(self.style.WARNING("Some data could not be parsed from:"))
            self.stdout.write(f"HTTP Response:\n {chapter_response}")
            self.stdout.write(f"Skipping download for {chapter_title} → {chapter_href}")
            return

        # Save metadata
        self.save_file(
            text=json.dumps(data["metadata"], sort_keys=True, indent=4),
            path=meta_path,
            clobber=bool(options.get("clobber")),
            success_msg=f'"{chapter_title}" metadata saved to {meta_path}',
            warn_msg=f"{meta_path} already exists. Not saving...",
        )

        if options.get("metadata_only"):
            return

        # Save source HTML
        self.save_file(
            text=data["html"],
            path=src_path,
            clobber=bool(options.get("clobber")),
            success_msg=f'"{chapter_title}" html saved to {src_path}',
            warn_msg=f"{src_path} already exists. Not saving...",
        )

        # Save cleaned HTML
        self.save_file(
            text=data["cleaned_html"],
            path=cleaned_src_path,
            clobber=bool(options.get("clobber")),
            success_msg=f'"{chapter_title}" html saved to {cleaned_src_path}',
            warn_msg=f"{src_path} already exists. Not saving...",
        )

        # Save text
        self.save_file(
            text=data["text"],
            path=txt_path,
            clobber=bool(options.get("clobber")),
            success_msg=f'"{chapter_title}" text saved to {txt_path}',
            warn_msg=f"{txt_path} already exists. Not saving...",
        )

        # Save author's note
        self.save_file(
            text=data["authors_note"],
            path=authors_note_path,
            clobber=bool(options.get("clobber")),
            success_msg=f'"{chapter_title}" text saved to {authors_note_path}',
            warn_msg=f"{authors_note_path} already exists. Not saving...",
        )

        self.last_download = time.time()

    def download_book(
        self, toc: get.TableOfContents, options: dict[str, Any], volume_title: str, book_title: str, book_path: Path
    ) -> None:
        book_path.mkdir(parents=True, exist_ok=True)
        chapters = toc.volume_data[volume_title][book_title]

        # Save metadata
        metadata: dict = {
            "title": book_title,
            "chapters": {k: i for (i, (k, _)) in enumerate(chapters.items())},
        }
        meta_path = Path(book_path, "metadata.json")
        self.save_file(
            text=json.dumps(metadata, sort_keys=True, indent=4),
            path=meta_path,
            clobber=bool(options.get("clobber")),
            success_msg=f'"{book_title}" metadata saved to {meta_path}',
            warn_msg=f"{meta_path} already exists. Not saving...",
        )

        for chapter_title in chapters:
            chapter_path = Path(book_path, chapter_title)
            self.download_chapter(toc, options, volume_title, book_title, chapter_title, chapter_path)

    def download_volume(
        self, toc: get.TableOfContents, options: dict[str, Any], volume_title: str, volume_path: Path
    ) -> None:
        volume_path.mkdir(parents=True, exist_ok=True)
        books = toc.volume_data[volume_title]

        # Save metadata
        metadata: dict = {
            "title": volume_title,
            "books": {k: i for (i, (k, _)) in enumerate(books.items())},
        }
        meta_path = Path(volume_path, "metadata.json")
        self.save_file(
            text=json.dumps(metadata, sort_keys=True, indent=4),
            path=meta_path,
            clobber=bool(options.get("clobber")),
            success_msg=f'"{volume_title}" metadata saved to {meta_path}',
            warn_msg=f"{meta_path} already exists. Not saving...",
        )

        for book_title in books:
            book_path = Path(volume_path, book_title)
            self.download_book(toc, options, volume_title, book_title, book_path)

    def handle(self, *_args, **options) -> None:  # noqa: ANN002, ANN003
        # TODO: fix Keyboard Exception not working
        try:
            throttle = float(options.get("throttle", 2.0))
        except ValueError:
            self.stdout.write(self.style.WARNING("Invalid throttle argument defaulting to 2.0 seconds."))
            throttle = 2.0

        self.session = get.Session(throttle=throttle)
        toc = get.TableOfContents(self.session)
        if len(toc.volume_data) == 0:
            self.stdout.write(self.style.WARNING("Volume data is empty. The Table of Contents may have changed..."))

        def download_latest_chapter() -> None:
            # TODO
            pass

        # TODO: add option to diff previous table of contents to check for
        # changes and only get the latest posted volumes/chapters
        try:
            if toc.response is None:
                msg = f"The table of contents ({toc.url}) could not be downloaded.\nCheck your network connection and confirm the host hasn't been IP blocked."
                raise CommandError(
                    msg,
                )

            v_title: str = options.get("volume", "")
            b_title: str = options.get("book", "")
            c_title: str = options.get("chapter", "")

            root = Path(options.get("root", ""))
            volume_root = options.get("volume_root", "")

            if root == "" or volume_root == "":
                msg = f"An invalid `root` {root} or `volume root` {volume_root} was provided."
                raise CommandError(msg)

            root = Path(root)
            root.mkdir(exist_ok=True)

            volume_root = Path(root, volume_root)
            volume_root.mkdir(exist_ok=True)

            # Get volumes/books/chapters
            if options.get("all"):
                # Save metadata
                metadata = {
                    "title": "The Wandering Inn",
                    "volumes": {k: i for i, k in enumerate(toc.volume_data)},
                }
                meta_path = Path(volume_root, "metadata.json")
                self.save_file(
                    text=json.dumps(metadata, sort_keys=True, indent=4),
                    path=meta_path,
                    clobber=bool(options.get("clobber")),
                    success_msg=f"Volumes metadata saved to {meta_path}",
                    warn_msg=f"{meta_path} already exists. Not saving...",
                )

                # Download all volumes
                for _i, (volume_title, _books) in list(enumerate(toc.volume_data.items())):
                    # TODO: check for empty volume_title
                    volume_path = Path(volume_root, f"{volume_title}")
                    self.download_volume(toc, options, volume_title, volume_path)
            elif c_title:
                # Download selected chapter
                path = Path(volume_root, v_title, b_title, c_title)
                self.download_chapter(toc, options, v_title, b_title, c_title, path)
            elif b_title:
                # Download selected book
                path = Path(volume_root, v_title, b_title)
                self.download_book(toc, options, v_title, b_title, path)
            elif v_title:
                # Download selected volume
                path = Path(volume_root, v_title)
                self.download_volume(toc, options, v_title, path)

        except KeyboardInterrupt as exc:
            # TODO: file / partial download cleanup
            msg = "Keyboard interrupt...downloads stopped"
            raise CommandError(msg) from exc

        # TODO add pause/resume
        # TODO add type hinting
        # TODO add chapter hashing to check for changes
        # TODO add chapter archiving functionality
        # TODO use urllib or requests to handle URLs
        # TODO add error handling
