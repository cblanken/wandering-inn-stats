from datetime import datetime as dt
from enum import Enum
import json
import logging
from pprint import pprint
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from stats.models import Color, ColorCategory, Chapter, Book, Volume, TextRef, RefType, Alias
from processing import Volume as SrcVolume, Book as SrcBook, Chapter as SrcChapter, get_metadata

class COLOR_CATEGORY(Enum):
    INVISIBLE = "Invisible skills/text"
    SIREN_WATER = "Siren water skill"
    CERIA_COLD = "Ceria cold skill"
    MAGNOLIA_CHARM = "Magnolia charm skill"
    FLYING_QUEEN = "Flying Queen talking"
    TWISTED_QUEEN = "Twisted Queen talking"
    ARMORED_QUEEN = "Armored Queen talking"
    SILENT_QUEEN = "Silent Queen talking and purple skills"
    GRAND_QUEEN = "Grand Queen talking"
    SPRING_FAE = "Spring fae talking"
    WINTER_FAE = "Winter fae talking"
    CLASS_RESTORATION = "Class restoration / Conviction skill"
    DIVINE_TEMP = "Divine/Temporary skills"
    ERIN_LANDMARK_SKILL = "Erin's landmark skill"
    UNIQUE_SKILL = "Unique skills"
    IVOLETHE_FIRE = "Ivolethe summoning fire"
    SER_RAIM = "Ser Raim skill"
    RED = "Red skills and classes"

COLORS: tuple[tuple] = (
    ("0C0E0E", COLOR_CATEGORY.INVISIBLE),
    ("00CCFF", COLOR_CATEGORY.SIREN_WATER),
    ("3366FF", COLOR_CATEGORY.CERIA_COLD),
    ("99CCFF", COLOR_CATEGORY.CERIA_COLD),
    ("CCFFFF", COLOR_CATEGORY.CERIA_COLD),
    ("FB00FF", COLOR_CATEGORY.MAGNOLIA_CHARM),
    ("FD78FF", COLOR_CATEGORY.MAGNOLIA_CHARM),
    ("FFB8FD", COLOR_CATEGORY.MAGNOLIA_CHARM),
    ("FDDBFF", COLOR_CATEGORY.MAGNOLIA_CHARM),
    ("99CC00", COLOR_CATEGORY.FLYING_QUEEN),
    ("993300", COLOR_CATEGORY.TWISTED_QUEEN),
    ("999999", COLOR_CATEGORY.ARMORED_QUEEN),
    ("CC99FF", COLOR_CATEGORY.SILENT_QUEEN),
    ("FFCC00", COLOR_CATEGORY.GRAND_QUEEN),
    ("96BE50", COLOR_CATEGORY.SPRING_FAE),
    ("8AE8FF", COLOR_CATEGORY.WINTER_FAE),
    ("99CCFF", COLOR_CATEGORY.CLASS_RESTORATION),
    ("FFD700", COLOR_CATEGORY.DIVINE_TEMP),
    ("FF9900", COLOR_CATEGORY.ERIN_LANDMARK_SKILL),
    ("99CC00", COLOR_CATEGORY.UNIQUE_SKILL),
    ("E01D1D", COLOR_CATEGORY.IVOLETHE_FIRE),
    ("EB0E0E", COLOR_CATEGORY.SER_RAIM),
    ("FF0000", COLOR_CATEGORY.RED)
)

def select_color_type(rgb_hex: str) -> COLOR_CATEGORY:
    """Interactive selection of ColorCategory"""
    colors = list(filter(lambda x: x[0] == rgb_hex.upper(), COLORS))
    if len(colors) == 0:
        return None
    elif len(colors) == 0:
        return colors[0]
    else:
        print("Select color. Options include: ")
        pprint(zip(range(len(colors)), colors))
        while True:
            try:
                sel = int(input("Selection: "))
                if sel >= len(colors):
                    raise ValueError
                return colors[sel]
            except ValueError:
                print("Invalid selection. Try again.")
                continue

def match_ref_type(type_str) -> str:
    match type_str[:2].upper():
        case "CL":
            return RefType.CLASS
        case "CO":
            return RefType.CLASS_OBTAINED
        case "SK":
            return RefType.SKILL
        case "SO":
            return RefType.SKILL_OBTAINED
        case "SP":
            return RefType.SPELL
        case "SB":
            return RefType.SPELL_OBTAINED
        case "CH":
            return RefType.CHARACTER
        case "IT":
            return RefType.ITEM
        case "LO":
            return RefType.LOCATION
        case _:
            return None

def select_ref_type() -> str:
    """Interactive classification of TextRef type"""
    try:
        while True:
            sel = input(f"Classify the above TextRef {RefType.TYPES} (leave blank to skip): ")

            if sel.strip() == "":
                return None # skip without confirmation
            if len(sel) < 2:
                print("Invalid selection.")
                yes_no = input("Try again (y/n)")
                if yes_no.lower() == "y":
                    continue
                return None # skip with confirmation
            
            ref_type = match_ref_type(sel)
            return ref_type


    except KeyboardInterrupt as exc:
        print("")
        raise CommandError("Build interrupted with Ctrl-C (Keyboard Interrupt).") from exc
    except EOFError as exc:
        print("")
        raise CommandError("Build interrupted with Ctrl-D (EOF).") from exc

class Command(BaseCommand):
    """Database build function"""
    help = "Update database from chapter source HTML and text files"

    def add_arguments(self, parser):
        parser.add_argument("volumes_path", type=str,
            help="Path in file system where chapter data is saved to disk per volume")
        parser.add_argument("-i", "--ignore-missing-chapter-metadata", action="store_true",
            help="Update Chapter data with defaults if the metadata file can't be read")
        # TODO: add (-u) option for updating existing records

    def handle(self, *args, **options):
        self.stdout.write("Updating DB...")

        # Populate ColorsCategory
        self.stdout.write("\nPopulating color categories...")
        for cat in COLOR_CATEGORY:
            try:
                category = ColorCategory.objects.get(name=cat.value)
                self.stdout.write(self.style.WARNING(f"> {category} already exists. Skipping creation..."))
            except ColorCategory.DoesNotExist:
                category = ColorCategory(name=cat.value)
                category.save()
                self.stdout.write(self.style.SUCCESS(f"> ColorCategory created: {category}"))

        # Populate Colors
        self.stdout.write("\nPopulating colors...")
        for col in COLORS:
            matching_category = ColorCategory.objects.get(name=col[1].value)
            try:
                color = Color.objects.get(rgb=col[0], category=matching_category)
                self.stdout.write(self.style.WARNING(f"> {color} already exists. Skipping creation..."))
            except Color.DoesNotExist:
                color = Color(rgb=col[0], category=matching_category)
                color.save()
                self.stdout.write(self.style.SUCCESS(f"> Color created: {color}"))


        # Populate Volumes
        vol_root = Path(options["volumes_path"])
        meta_path = Path(vol_root)
        volumes_metadata = get_metadata(meta_path)
        volumes = sorted(list(volumes_metadata["volumes"].items()), key=lambda x: x[1])

        for (vol_title, vol_num) in volumes:
            src_vol: SrcVolume = SrcVolume(Path(vol_root, vol_title))
            try:
                volume = Volume.objects.get(title=src_vol.title)
                self.stdout.write(
                    self.style.WARNING(f"> Record for {src_vol.title} already exists. Skipping creation...")
                )
            except Volume.DoesNotExist:
                volume = Volume(number=vol_num, title=src_vol.title)
                volume.save()
                self.stdout.write(self.style.SUCCESS(f"> Volume created: {volume}"))

            # Populate Books
            for (book_num, book_title) in enumerate(src_vol.books):
                src_book: SrcBook = SrcBook(Path(src_vol.path, book_title))
                try:
                    book = Book.objects.get(title=book_title)
                    self.stdout.write(
                        self.style.WARNING(f"> Record for {book_title} already exists. Skipping creation...")
                    )
                except Book.DoesNotExist:
                    book = Book(number=book_num, title=book_title, volume=volume)
                    self.stdout.write(self.style.SUCCESS(f"> Book created: {book}"))
                    book.save()

                # Populate Chapters
                for (chapter_num, chapter_title) in enumerate(src_book.chapters):
                    src_chapter: SrcChapter = SrcChapter(Path(src_book.path, chapter_title))
                    try:
                        # Check for existing Chapter
                        chapter = Chapter.objects.get(title=src_chapter.title)
                        self.stdout.write(self.style.WARNING(f"> {src_chapter.title} already exists. Skipping creation..."))
                    except Chapter.DoesNotExist:
                        chapter = Chapter(
                            number=chapter_num, title=src_chapter.title, book=book,
                            is_interlude="interlude" in src_chapter.title.lower(),
                            source_url=src_chapter.metadata.get("url", ""),
                            post_date=dt.fromisoformat(src_chapter.metadata.get("pub_time", dt.now().isoformat())),
                            last_update=dt.fromisoformat(src_chapter.metadata.get("mod_time", dt.now().isoformat())),
                            download_date=dt.fromisoformat(src_chapter.metadata.get("dl_time", dt.now().isoformat())),
                            word_count=src_chapter.metadata.get("word_count", 0)
                        )
                        self.stdout.write(self.style.SUCCESS(f"> Chapter created: {chapter}"))
                        chapter.save()

                    # Populate TextRefs
                    for ref in src_chapter.all_text_refs:
                        print(ref)

                        selected_type = None
                        try:
                            # Check for existing RefType
                            ref_type = RefType.objects.get(name=ref.text)
                            self.stdout.write(self.style.WARNING(f"> [{ref.text}] already exists. Skipping creation..."))
                            selected_type = ref_type.type
                        except RefType.DoesNotExist:
                            # Check for existing Alias
                            try:
                                alias = Alias.objects.get(name=ref.text)
                                selected_type = alias.ref_type.type
                                self.stdout.write(self.style.WARNING(f"> {alias} already exists. Skipping creation..."))
                            except Alias.DoesNotExist:
                                selected_type = select_ref_type()
                                if selected_type is not None:
                                    ref_type = RefType(name=ref.text, type=selected_type)
                                    ref_type.save()
                                    self.stdout.write(self.style.SUCCESS(f"> {ref_type} created"))
                                else:
                                    self.stdout.write(self.style.WARNING(f"> {ref.text} skipped..."))

                        if selected_type is not None:
                            try:
                                text_ref = TextRef.objects.get(
                                    chapter=chapter,
                                    type=ref_type,
                                    line_number=ref.line_number,
                                    start_column=ref.start_column,
                                )
                                self.stdout.write(
                                    self.style.WARNING(f"> [{text_ref.text}] already exists. Skipping creation...")
                                )
                            except TextRef.DoesNotExist:
                                text_ref = TextRef(
                                    text=ref.text,
                                    type=ref_type,
                                    chapter=chapter,
                                    line_number=ref.line_number,
                                    start_column=ref.start_column,
                                    end_column = ref.end_column,
                                    context_offset = ref.context_offset,
                                )

                                text_ref.save()
                                self.stdout.write(self.style.SUCCESS(f"> {text_ref} created"))

                    vol_num += 1
