"""Download command for wanderinginn.com"""

import json
from pathlib import Path
import random
import time
from django.core.management.base import BaseCommand, CommandError
from processing import get


class Command(BaseCommand):
    help = "Download Wandering Inn data including volumes, books, chapters, characters etc."
    last_download: float = 0.0
    session = get.Session()

    def add_arguments(self, parser):
        parser.add_argument("volume", nargs="?", type=str, help="Volume to download")
        parser.add_argument("book", nargs="?", type=str, help="Book to download")
        parser.add_argument("chapter", nargs="?", type=str, help="Chapter to download")
        parser.add_argument(
            "-a", "--all", action="store_true", help="Download all volumes"
        )
        parser.add_argument(
            "-i",
            "--index",
            action="store_true",
            help="Retrieve volume/book/chapter by indexes instead of title",
        )
        parser.add_argument("-d", "--request_delay", default=5.0, help="Time delay")
        parser.add_argument(
            "-j",
            "--jitter",
            action="store_true",
            help="Randomized delay betweeen (0.5 to 1.5) times. By default, 5 seconds",
        )
        # TODO: update --jitter to use `const` argument type option
        parser.add_argument(
            "-r", "--root", default="./data", help="Root path of downloaded data"
        )
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
        parser.add_argument(
            "-m", "--metadata-only", action="store_true", help="Download only metadata"
        )
        parser.add_argument(
            "--classes",
            action="store_true",
            help="Download class information from wiki",
        )
        parser.add_argument(
            "--skills", action="store_true", help="Download skill information from wiki"
        )
        parser.add_argument(
            "--spells", action="store_true", help="Download spell information from wiki"
        )
        parser.add_argument(
            "--chars",
            action="store_true",
            help="Download character information from wiki",
        )
        parser.add_argument(
            "--locs",
            action="store_true",
            help="Download location information from wiki",
        )

    def save_file(
        self,
        text: str,
        path: Path,
        clobber: bool,
        success_msg: str = "",
        warn_msg: str = "",
    ):
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

    def download_wiki_info(self, options: dict[str, str]):
        root_path = options.get("root")
        if root_path is None:
            return

        # Get class info
        if options.get("classes"):
            self.stdout.write("Downloading class information...")
            classes = self.session.get_class_list()

            class_data_path = Path(root_path, "classes.txt")
            self.save_file(
                text="\n".join(classes),
                path=class_data_path,
                clobber=bool(options.get("clobber")),
                success_msg=f"Character data saved to {class_data_path}",
                warn_msg=f"{class_data_path} already exists. Not saving...",
            )

        # Get skill info
        if options.get("skills"):
            self.stdout.write("Downloading skill information...")
            skills = self.session.get_skill_list()

            skill_data_path = Path(root_path, "skills.txt")
            self.save_file(
                text="\n".join(skills),
                path=skill_data_path,
                clobber=bool(options.get("clobber")),
                success_msg=f"Character data saved to {skill_data_path}",
                warn_msg=f"{skill_data_path} already exists. Not saving...",
            )

        # Get spell info
        if options.get("spells"):
            self.stdout.write("Downloading spell information...")
            spells = self.session.get_spell_list()

            spell_data_path = Path(root_path, "spells.txt")
            self.save_file(
                text="\n".join(spells),
                path=spell_data_path,
                clobber=bool(options.get("clobber")),
                success_msg=f"Spell data saved to {spell_data_path}",
                warn_msg=f"{spell_data_path} already exists. Not saving...",
            )

        # Get location info
        if options.get("locs"):
            self.stdout.write("Downloading location information...")
            locs_by_alpha = self.session.get_all_locations_by_alpha()
            data = {}
            for locs in locs_by_alpha.values():
                for loc in locs.items():
                    data[loc[0]] = {"url": loc[1]}

            loc_data_path = Path(root_path, "locations.json")
            self.save_file(
                text=json.dumps(data, sort_keys=True, indent=4),
                path=loc_data_path,
                clobber=bool(options.get("clobber")),
                success_msg=f"Location data saved to {loc_data_path}",
                warn_msg=f"{loc_data_path} already exists. Not saving...",
            )

        # Get character info
        if options.get("chars"):
            self.stdout.write("Downloading character information...")
            data = self.session.get_all_character_data()

            char_data_path = Path(root_path, "characters.json")
            self.save_file(
                text=json.dumps(data, sort_keys=True, indent=4),
                path=char_data_path,
                clobber=bool(options.get("clobber")),
                success_msg=f"Character data saved to {char_data_path}",
                warn_msg=f"{char_data_path} already exists. Not saving...",
            )

    def download_chapter(
        self,
        toc,
        options,
        volume_title: str,
        book_title: str,
        chapter_title: str,
        chapter_path: Path,
    ):
        try:
            chapter_href = toc.volume_data[volume_title][book_title][chapter_title]
        except KeyError as exc:
            self.stdout.write(self.style.WARNING(f"Could not find {exc}"))
            return

        # Download chapter
        chapter_path.mkdir(parents=True, exist_ok=True)
        src_path = Path(chapter_path, f"{chapter_title}.html")
        txt_path = Path(chapter_path, f"{chapter_title}.txt")
        authors_note_path = Path(chapter_path, f"{chapter_title}_authors_note.txt")
        meta_path = Path(chapter_path, "metadata.json")

        if (
            not options.get("clobber")
            and src_path.exists()
            and txt_path.exists()
            and meta_path.exists()
        ):
            self.stdout.write(
                self.style.NOTICE(
                    f'> All chapter files exist for chapter: "{chapter_title}". Skipping...'
                )
            )
            return

        self.stdout.write(f"Downloading {chapter_href}")
        chapter_response = self.session.get(chapter_href)
        if chapter_response is None:
            self.stdout.write(self.style.WARNING("! Chapter could not be downloaded!"))
            self.stdout.write(f"Skipping download for {chapter_title} → {chapter_href}")
            self.session.reset_tries()
            return

        data = get.parse_chapter(chapter_response)

        if (
            data.get("html") is None
            or data.get("text") is None
            or data.get("metadata") is None
        ):
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
        self, toc, options, volume_title: str, book_title: str, book_path: Path
    ):
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
            self.download_chapter(
                toc, options, volume_title, book_title, chapter_title, chapter_path
            )

    def download_volume(self, toc, options, volume_title: str, volume_path: Path):
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

    def handle(self, *args, **options) -> None:
        # TODO: fix Keyboard Exception not working
        toc = get.TableOfContents(self.session)
        if len(toc.volume_data) == 0:
            self.stdout.write(
                self.style.WARNING(
                    "Volume data is empty. The Table of Contents may have changed..."
                )
            )
        self.last_download: int = 0

        def download_last_chapter():
            # TODO
            pass

        # TODO: add option to diff previous table of contents to check for
        # changes and only get the latest posted volumes/chapters
        try:
            if toc.response is None:
                raise CommandError(
                    f"The table of contents ({toc.url}) could not be downloaded.\nCheck your network connection and confirm the host hasn't been IP blocked."
                )

            v_title: str = options.get("volume", "")
            b_title: str = options.get("book", "")
            c_title: str = options.get("chapter", "")

            root = Path(options.get("root", ""))
            volume_root = options.get("volume_root", "")

            if root == "" or volume_root == "":
                raise CommandError(
                    f"An invalid `root` {root} or `volume root` {volume_root} was provided."
                )

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
                for i, (volume_title, books) in list(
                    enumerate(toc.volume_data.items())
                ):
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

            self.download_wiki_info(options)

        except KeyboardInterrupt as exc:
            # TODO: file / partial download cleanup
            raise CommandError("Keyboard interrupt...downloads stopped") from exc

        # TODO add pause/resume
        # TODO add type hinting
        # TODO add chapter hashing to check for changes
        # TODO add chapter archiving functionality
        # TODO use urllib or requests to handle URLs
        # TODO add error handling
