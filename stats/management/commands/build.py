from datetime import datetime as dt
from enum import Enum
import json
import logging
from pprint import pprint
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db.models.query import QuerySet
from stats.models import (
    Color, ColorCategory, Chapter, Book, Volume, TextRef, RefType, Alias, Character
)
from processing import (
    Volume as SrcVolume, Book as SrcBook, Chapter as SrcChapter, get_metadata
)

class COLOR_CATEGORY(Enum):
    """Text color categories according to TWI wiki"""
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
        parser.add_argument("data_path", type=str,
            help="Path in file system where build data is saved to disk. \
                This includes volumes, books, chapters, characters, etc.")
        parser.add_argument("-i", "--ignore-missing-chapter-metadata", action="store_true",
            help="Update Chapter data with defaults if the metadata file can't be read")
        # TODO: add (-u) option for updating existing records

    def handle(self, *args, **options):
        self.stdout.write("Updating DB...")

        def get_or_create_ref_type(text_ref: TextRef) -> RefType:
            # Check for existing RefType
            try:
                ref_type = RefType.objects.get(name=text_ref.text)
                self.stdout.write(self.style.WARNING(
                    f"> RefType: {text_ref.text} already exists. Skipping creation..."))
                return ref_type
            except RefType.DoesNotExist:
                pass

            # Check for existing Alias
            try:
                alias = Alias.objects.get(name=text_ref.text)

                if alias:
                    self.stdout.write(self.style.WARNING(
                        f"> Alias exists for RefType {text_ref.text} already. Skipping creation..."))
                    return alias.ref_type
            except Alias.DoesNotExist:
                pass

            # Check for alternate forms of RefType (pluralized, gendered, etc.)
            ref_name = text_ref.text[1:-1] if text_ref.is_bracketed else text_ref.text

            singular_ref_type_qs = None
            singular_name_candidates = []
            if ref_name.endswith("s"):
                singular_name_candidates.append(f"[{ref_name[:-1]}]" if text_ref.is_bracketed else ref_name.text[:-1])
            if ref_name.endswith("es"):
              singular_name_candidates.append(f"[{ref_name[:-2]}]" if text_ref.is_bracketed else ref_name.text[:-2])
            if ref_name.endswith("ies"):
              singular_name_candidates.append(f"[{ref_name[:-3]}]" if text_ref.is_bracketed else ref_name.text[:-3])
            if ref_name.endswith("man"):
              singular_name_candidates.append(f"[{ref_name[:-3]}]" if text_ref.is_bracketed else ref_name.text[:-3])
            if ref_name.endswith("woman"):
              singular_name_candidates.append(f"[{ref_name[:-5]}]" if text_ref.is_bracketed else ref_name.text[:-5])
            if ref_name.endswith("men"):
              singular_name_candidates.append(f"[{ref_name[:-3]}]" if text_ref.is_bracketed else ref_name.text[:-3])
            if ref_name.endswith("women"):
                singular_name_candidates.append(f"[{ref_name[:-5]}]" if text_ref.is_bracketed else ref_name.text[:-5])

            for c in singular_name_candidates:
                singular_ref_type_qs = RefType.objects.filter(name=c)
                singular_alias_qs = Alias.objects.filter(name=c)
                if singular_ref_type_qs.exists():
                    # The TextRef is an alternate version of an existing RefType
                    ref_type = singular_ref_type_qs[0]
                elif singular_alias_qs.exists():
                    # The TextRef is an alternate version of an existing Alias
                    ref_type = singular_alias_qs[0].ref_type
                else:
                    continue

                # Create Alias to base RefType
                alias, created = Alias.objects.get_or_create(name=text_ref.text, ref_type=ref_type)
                prelude = f"> RefType: {text_ref.text} did not exist, but it is a pluralized form of {ref_name}. "
                if created:
                    self.stdout.write(self.style.SUCCESS(prelude +
                        f"No existing Alias was found, so one was created."))
                else:
                    self.stdout.write(self.style.WARNING(prelude +
                        f"An existing Alias was found, so none were created."))
                return alias.ref_type


            # Could not find existing RefType or Alias or alternate form
            # Prompt user to select TextRef type
            new_type = select_ref_type()
            
            # RefType was NOT categorized, so skip
            if new_type is None:
                self.stdout.write(self.style.WARNING(f"> {text_ref.text} manually skipped..."))
                return None

            # Create RefType
            new_ref_type = RefType(name=text_ref.text, type=new_type)
            new_ref_type.save()
            self.stdout.write(self.style.SUCCESS(f"> {new_ref_type} created"))
            return new_ref_type

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

        # Populate spell types from wiki data
        self.stdout.write("\nPopulating spell RefType(s)...")
        spell_data_path = Path(options["data_path"], "spells.tsv")
        with open(spell_data_path, encoding="utf-8") as file:
            for line in file.readlines():
                line = line.strip().split("|")
                aliases = []
                if len(line) > 1:
                    # Spell with aliases
                    spell_name, *aliases = line
                else:
                    spell_name = line[0]

                spell = "[" + spell_name + "]"
                ref_type, ref_type_created = RefType.objects.get_or_create(name=spell, type=RefType.SPELL)

                if ref_type_created:
                    self.stdout.write(self.style.SUCCESS(f"> {ref_type} created"))
                else:
                    self.stdout.write(self.style.WARNING(f"> Spell RefType: {spell} already exists. Skipping creation..."))

                for alias_name in aliases:
                    new_alias, new_alias_created = Alias.objects.get_or_create(
                        name=alias_name, ref_type=ref_type)
                    if new_alias_created:
                        self.stdout.write(self.style.SUCCESS(f"> Alias: {alias_name} created"))
                    else:
                        self.stdout.write(self.style.WARNING(f"> Alias: {alias_name} already exists. Skipping creation..."))


        # Populate class types from wiki data
        self.stdout.write("\nPopulating class RefType(s)...")
        class_data_path = Path(options["data_path"], "classes.txt")
        with open(class_data_path, encoding="utf-8") as file:
            for line in file.readlines():
                class_name = "[" + line.strip() + "]"
                ref_type, ref_type_created = RefType.objects.get_or_create(name=class_name, type=RefType.CLASS)

                if ref_type_created:
                    self.stdout.write(self.style.SUCCESS(f"> {ref_type} created"))
                else:
                    self.stdout.write(self.style.WARNING(f"> Class RefType: {class_name} already exists. Skipping creation..."))

        # Populate characters from wiki data
        self.stdout.write("\nPopulating character RefType(s)...")
        char_data_path = Path(options["data_path"], "characters.json")
        with open(char_data_path, encoding="utf-8") as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                self.stdout.write(self.style.ERROR(
                    f"> Character data ({char_data_path}) could not be decoded"))
            else:
                for name, char_data in data.items():
                    # Create Character RefType
                    ref_type, ref_type_created = RefType.objects.get_or_create(
                        name=name, type=RefType.CHARACTER)
                    if ref_type_created:
                        self.stdout.write(self.style.SUCCESS(f"> Character RefType: {name} created"))
                    else:
                        self.stdout.write(self.style.WARNING(f"> Character RefType: {name} already exists. Skipping creation..."))

                    # Create aliases from Character wiki metadata
                    aliases = char_data.get("aliases")
                    if aliases is not None:
                        for alias_name in char_data.get("aliases"):
                            try:
                                Alias.objects.get(name=alias_name)
                                self.stdout.write(self.style.WARNING(f"> Alias: {alias_name} already exists. Skipping creation..."))
                            except Alias.DoesNotExist:
                                self.stdout.write(self.style.SUCCESS(f"> Alias: {alias_name} created"))
                                alias = Alias.objects.create(name=alias_name, ref_type=ref_type)
                                alias.save

                    # Create Character Data
                    new_character, new_char_created = Character.objects.get_or_create(
                        ref_type=ref_type,
                        first_ref_uri=char_data.get("first_href"),
                        wiki_uri=char_data.get("wiki_href"),
                        status=Character.parse_status_str(char_data.get("status")),
                        # species=char_data.get("species")
                    )
                    if new_char_created:
                        self.stdout.write(self.style.SUCCESS(f"> Character data: {name} created"))
                    else:
                        self.stdout.write(self.style.WARNING(f"> Character data: {name} already exists. Skipping creation..."))

        # Populate locations from wiki data
        self.stdout.write("\nPopulating locations RefType(s)...")
        loc_data_path = Path(options["data_path"], "locations.json")
        with open(loc_data_path, encoding="utf-8") as file:
            try:
                char_data = json.load(file)
            except json.JSONDecodeError:
                self.stdout.write(self.style.ERROR(
                    f"> location data ({loc_data_path}) could not be decoded"))
            else:
                for loc_name, char_data in char_data.items():
                    loc_url = char_data["url"]
                    ref_type, ref_type_created = RefType.objects.get_or_create(name=loc_name, type=RefType.LOCATION, description=loc_url)
                    if ref_type_created:
                        self.stdout.write(
                            self.style.SUCCESS(f"> Location RefType: {loc_name} created"))
                    else:
                        self.stdout.write(
                            self.style.WARNING(f"> location RefType: {loc_name} already exists. Skipping creation..."))

        # Populate Volumes
        vol_root = Path(options["data_path"], "volumes")
        meta_path = Path(vol_root)
        volumes_metadata = get_metadata(meta_path)
        volumes = sorted(list(volumes_metadata["volumes"].items()), key=lambda x: x[1])

        for (vol_title, vol_num) in volumes:
            src_vol: SrcVolume = SrcVolume(Path(vol_root, vol_title))
            volume, ref_type_created = Volume.objects.get_or_create(title=src_vol.title, number=vol_num)
            if ref_type_created:
                self.stdout.write(self.style.SUCCESS(f"> Volume created: {volume}"))
            else:
                self.stdout.write(
                    self.style.WARNING(f"> Record for {src_vol.title} already exists. Skipping creation...")
                )

            # Populate Books
            for (book_num, book_title) in enumerate(src_vol.books):
                src_book: SrcBook = SrcBook(Path(src_vol.path, book_title))
                book, book_created = Book.objects.get_or_create(title=book_title, number=book_num, volume=volume)
                if book_created:
                    self.stdout.write(self.style.SUCCESS(f"> Book created: {book}"))
                else:
                    self.stdout.write(
                        self.style.WARNING(f"> Record for {book_title} already exists. Skipping creation...")
                    )

                # Populate Chapters
                for (chapter_num, chapter_title) in enumerate(src_book.chapters):
                    src_chapter: SrcChapter = SrcChapter(Path(src_book.path, chapter_title))
                    if src_chapter.metadata is None:
                        self.stdout.write(self.style.SUCCESS(f"> Missing metadata for Chapter: {src_chapter.title}. Skipping..."))
                        continue
                    chapter, ref_type_created = Chapter.objects.get_or_create(
                        number=chapter_num, title=src_chapter.title, book=book,
                        is_interlude="interlude" in src_chapter.title.lower(),
                        source_url=src_chapter.metadata.get("url", ""),
                        post_date=dt.fromisoformat(src_chapter.metadata.get("pub_time", dt.now().isoformat())),
                        last_update=dt.fromisoformat(src_chapter.metadata.get("mod_time", dt.now().isoformat())),
                        download_date=dt.fromisoformat(src_chapter.metadata.get("dl_time", dt.now().isoformat())),
                        word_count=src_chapter.metadata.get("word_count", 0)
                    )

                    if ref_type_created:
                        self.stdout.write(self.style.SUCCESS(f"> Chapter created: {chapter}"))
                    else:
                        self.stdout.write(self.style.WARNING(
                            f"> Chapter \"{src_chapter.title}\" already exists. Skipping creation..."))

                    # Populate TextRefs
                    for text_ref in src_chapter.all_src_refs:
                        print(text_ref)

                        ref_type = get_or_create_ref_type(text_ref)

                        # RefType creation could not complete or was skipped
                        if ref_type is None:
                            continue

                        # Detect TextRef color
                        color = None
                        if 'span style="color:' in text_ref.context:
                            try:
                                print(f"Found color span in '{text_ref.context}'")
                                i: int = text_ref.context.index("color:")
                                # TODO: make this parsing more robust
                                rgb_hex: str = text_ref.context[i+7:i+13].upper()
                                matching_colors: QuerySet = Color.objects.filter(rgb=rgb_hex)
                                if len(matching_colors) == 1:
                                    color = matching_colors[0]
                                else:
                                    self.stdout.write(f"Unable to automatically select color for TextRef: {text_ref}")
                                    sel: int = 0
                                    for i, col in enumerate(matching_colors):
                                        self.stdout.write(f"{i}: {col}")
                                    # TODO: fix this select color prompt
                                    # triggers when no valid colors avaiale, add skip option
                                    while True:
                                        try:
                                            sel: int = int(input("Select color: "))
                                        except ValueError:
                                            self.stdout.write("Invalid selection. Please try again.")
                                            continue
                                        else:
                                            if sel < len(matching_colors):
                                                break
                                            self.stdout.write("Invalid selection. Please try again.")

                                    color = matching_colors[i]
                            except IndexError:
                                print("Can't get color. Invalid TextRef context index")
                                raise
                            except Color.DoesNotExist:
                                print("Can't get color. There is no existing Color for rgb={rgb_hex}")
                                raise
                            except KeyboardInterrupt as exc:
                                print("")
                                raise CommandError("Build interrupted with Ctrl-C (Keyboard Interrupt).") from exc
                            except EOFError as exc:
                                print("")
                                raise CommandError("Build interrupted with Ctrl-D (EOF).") from exc

                        # Create TextRef
                        text_ref, ref_type_created = TextRef.objects.get_or_create(
                            text=text_ref.text,
                            type=ref_type,
                            color=color,
                            chapter=chapter,
                            line_number=text_ref.line_number,
                            start_column=text_ref.start_column,
                            end_column = text_ref.end_column,
                            context_offset = text_ref.context_offset,
                        )
                        if ref_type_created:
                            self.stdout.write(self.style.SUCCESS(f"> {text_ref} created"))
                        else:
                            self.stdout.write(
                                self.style.WARNING(f"> TextRef: {text_ref.text} @line {text_ref.line_number} already exists. Skipping creation...")
                            )

