from datetime import datetime as dt
from enum import Enum
from glob import glob
import itertools
import json
import logging
from pprint import pprint
from pathlib import Path
import re
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.db.models.query import QuerySet
from stats.models import (
    Color, ColorCategory, Chapter, Book, Volume, TextRef, RefType, Alias, Character
)
from processing import (
    Volume as SrcVolume, Book as SrcBook, Chapter as SrcChapter, TextRef as SrcTextRef, get_metadata
)
from playsound import playsound, PlaysoundException

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
    RYOKA_MAUDLIN = "Ryoka's guilt/depression"
    RYOKA_HATE = "Ryoka's rage/indignation/self-hate"
    DARKNESS = "Darkness / fading light"

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
    ("FEEDFF", COLOR_CATEGORY.MAGNOLIA_CHARM),
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
    ("FF0000", COLOR_CATEGORY.RED),
    ("9FC5E8", COLOR_CATEGORY.RYOKA_MAUDLIN),
    ("EA9999", COLOR_CATEGORY.RYOKA_HATE),
    ("787878", COLOR_CATEGORY.DARKNESS),
    ("333333", COLOR_CATEGORY.DARKNESS)
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

def prompt(s: str = "", sound: bool = False):
    if sound:
        try:
            playsound(Path("stats/sounds/alert.mp3"), block=False)
        except PlaysoundException:
            pass

    return input(s)

def select_ref_type(sound: bool = False) -> str:
    """Interactive classification of TextRef type"""
    try:
        while True:
            sel = prompt(f"Classify the above TextRef with {RefType.TYPES} (leave blank to skip OR use \"r\" to retry): ", sound)

            if sel.strip().lower() == "r":
                return "retry" # special case to retry RefType acquisition
            if sel.strip() == "":
                return None # skip without confirmation
            if len(sel) < 2:
                print("Invalid selection.")
                yes_no = prompt("Try again (y/n): ", sound)
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

def select_ref_type_from_qs(query_set: QuerySet[RefType], sound: bool = False) -> str:
    """Interactive selection of an existing set of RefType(s)"""
    try:
        while True:
            for i, ref_type in enumerate(query_set):
                print(f"{i}: {ref_type.name} - {match_ref_type(ref_type.type)}")

            sel = prompt(f"Select one of the RefType(s) from the above options (leave empty to skip): ", sound)

            if sel.strip() == "":
                return None # skip without confirmation
            try:
                sel = int(sel)
            except ValueError:
                sel = -1 # invalid selection

            if sel >= 0 and sel < len(query_set):
                return query_set[sel]
            else:
                print("Invalid selection.")
                yes_no = prompt("Try again (y/n): ", sound)
                if yes_no.lower() == "y":
                    continue
                return None # skip with confirmation

    except KeyboardInterrupt as exc:
        print("")
        raise CommandError("Build interrupted with Ctrl-C (Keyboard Interrupt).") from exc
    except EOFError as exc:
        print("")
        raise CommandError("Build interrupted with Ctrl-D (EOF).") from exc


class Command(BaseCommand):
    """Database build function"""
    help = "Update database from chapter source HTML and data files"

    def add_arguments(self, parser):
        parser.add_argument("data_path", type=str,
            help="Path in file system where build data is saved to disk. \
                This includes volumes, books, chapters, characters, etc.")
        parser.add_argument("-i", "--ignore-missing-chapter-metadata", action="store_true",
            help="Update Chapter data with defaults if the metadata file can't be read")
        parser.add_argument("--skip-text-refs", action="store_true",
            help="Skip TextRef generation for each Chapter")
        parser.add_argument("--skip-wiki-chars", action="store_true",
            help="Skip Character wiki data build section")
        parser.add_argument("--skip-wiki-spells", action="store_true",
            help="Skip [Spell] wiki data build section")
        parser.add_argument("--skip-wiki-classes", action="store_true",
            help="Skip [Class] wiki data build section")
        parser.add_argument("--skip-wiki-skills", action="store_true",
            help="Skip [Skill] wiki data build section")
        parser.add_argument("--skip-wiki-locs", action="store_true",
            help="Skip location wiki data build section")
        parser.add_argument("--skip-wiki-all", action="store_true",
            help="Skip all wiki data build sections")
        parser.add_argument("--skip-reftype-select", action="store_true",
            help="Skip RefType prompt for unknown RefTypes")
        parser.add_argument("--skip-textref-color-select", action="store_true",
            help="Disable TextRef selection prompt for ambiguous TextRef colors")
        parser.add_argument("--prompt-sound", action="store_true",
            help="Play short alert sound when build stops with a user prompt")
        parser.add_argument("--chapter-id", type=int, default=None,
            help="Download a specific chapter by ID number")
        parser.add_argument("--chapter-id-range", type=str, default=None,
            help="Download a range of chapters by ID number")
        # TODO: add (-u) option for updating existing records

    def handle(self, *args, **options):
        if options.get("skip_wiki_all"):
            options["skip_wiki_chars"] = True
            options["skip_wiki_locs"] = True
            options["skip_wiki_spells"] = True
            options["skip_wiki_classes"] = True
            options["skip_wiki_skills"] = True

        self.stdout.write("Updating DB...")
        def get_or_create_ref_type(text_ref: TextRef) -> RefType:
            # Check for existing RefType and create if necessary
            while True: # loop for retries from select RefeType prompt
                try:
                    ref_type = RefType.objects.get(name=text_ref.text)
                    self.stdout.write(self.style.WARNING(
                        f"> RefType: {text_ref.text} already exists. Skipping creation..."))
                    return ref_type
                except RefType.DoesNotExist:
                    ref_type = None
                except RefType.MultipleObjectsReturned:
                    ref_types = RefType.objects.filter(name=text_ref.text)
                    self.stdout.write(self.style.WARNING(f"> Multiple RefType(s) exist for the name: {text_ref.text}..."))
                    ref_type = select_ref_type_from_qs(ref_types, sound=True)
                    return ref_type

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
                    singular_name_candidates.append(f"[{ref_name[:-3]}y]" if text_ref.is_bracketed else ref_name.text[:-3])
                if ref_name.endswith("men"):
                    singular_name_candidates.append(f"[{ref_name[:-3]}man]" if text_ref.is_bracketed else ref_name.text[:-3])
                if ref_name.endswith("women"):
                    singular_name_candidates.append(f"[{ref_name[:-5]}woman]" if text_ref.is_bracketed else ref_name.text[:-5])
                
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
                    prelude = f"> RefType: {text_ref.text} did not exist, but it is a pluralized form of {ref_type.name}. "
                    if created:
                        self.stdout.write(self.style.SUCCESS(prelude +
                            f"No existing Alias was found, so one was created."))
                    else:
                        self.stdout.write(self.style.WARNING(prelude +
                            f"An existing Alias was found, so none were created."))
                    return alias.ref_type


                # Could not find existing RefType or Alias or alternate form so
                # intialize type for new RefType

                # Check for [Skill] or [Class] acquisition messages
                skill_obtained_pattern = re.compile(r'^\[Skill.*[Oo]btained.*\]$')
                class_obtained_pattern = re.compile(r'^\[.*Class\W[Oo]btained.*\]$')
                if skill_obtained_pattern.match(text_ref.text):
                    new_type = RefType.SKILL_OBTAINED
                elif class_obtained_pattern.match(text_ref.text):
                    new_type = RefType.CLASS_OBTAINED
                else:
                    # Prompt user to select TextRef type
                    if options.get("skip_reftype_select"):
                        new_type = None
                    else:
                        new_type = select_ref_type(sound=options.get("prompt_sound"))
                        if new_type == "retry":
                            continue # retry RefType acquisition
                
                # RefType was NOT categorized, so skip
                if new_type is None:
                    self.stdout.write(self.style.WARNING(f"> {text_ref.text} skipped..."))
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
        if not options.get("skip_wiki_spells"):
            self.stdout.write("\nPopulating spell RefType(s)...")
            spell_data_path = Path(options["data_path"], "spells.txt")
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
                        alias_name = "[" + alias_name + "]"
                        new_alias, new_alias_created = Alias.objects.get_or_create(
                            name=alias_name, ref_type=ref_type)
                        if new_alias_created:
                            self.stdout.write(self.style.SUCCESS(f"> Alias: {alias_name} created"))
                        else:
                            self.stdout.write(self.style.WARNING(f"> Alias: {alias_name} already exists. Skipping creation..."))
        
        if not options.get("skip_wiki_skills"):
            self.stdout.write("\nPopulating spell RefType(s)...")
            skill_data_path = Path(options["data_path"], "skills.txt")
            with open(skill_data_path, encoding="utf-8") as file:
                for line in file.readlines():
                    skill, *aliases = ["[" + name + "]" for name in line.strip().split("|")]
                    
                    ref_type, ref_type_created = RefType.objects.get_or_create(name=skill, type=RefType.SKILL)
                    if ref_type_created:
                        self.stdout.write(self.style.SUCCESS(f"> {ref_type} created"))
                    else:
                        self.stdout.write(self.style.WARNING(f"> Skill RefType: {skill} already exists. Skipping creation..."))

                    for alias_name in aliases:
                        new_alias, new_alias_created = Alias.objects.get_or_create(
                            name=alias_name, ref_type=ref_type)
                        if new_alias_created:
                            self.stdout.write(self.style.SUCCESS(f"> Alias: {alias_name} created"))
                        else:
                            self.stdout.write(self.style.WARNING(f"> Alias: {alias_name} already exists. Skipping creation..."))


        # Populate class types from wiki data
        if not options.get("skip_wiki_classes"):
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
        if not options.get("skip_wiki_chars"):
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

                        # Create alias for Character first name
                        invalid_first_names = [
                            "a", "the", "an", "gnoll", "drake", "human", "elf", "half-elf",
                            "dullahan", "selphid", "goblin", "harpy", "halfling"
                        ]
                        name_split = name.strip().split(" ")
                        if len(name_split) > 0 and name_split[0].lower() not in invalid_first_names and name_split[0] != name:
                            try:
                                Alias.objects.get(name=name_split[0])
                                self.stdout.write(self.style.WARNING(f"> Alias: {name_split[0]} already exists. Skipping creation..."))
                            except Alias.DoesNotExist:
                                self.stdout.write(self.style.SUCCESS(f"> Alias: {name_split[0]} created"))
                                Alias.objects.create(name=name_split[0], ref_type=ref_type)

                        # Create aliases from Character wiki metadata
                        aliases = char_data.get("aliases")
                        if aliases is not None:
                            for alias_name in char_data.get("aliases"):
                                try:
                                    Alias.objects.get(name=alias_name)
                                    self.stdout.write(self.style.WARNING(f"> Alias: {alias_name} already exists. Skipping creation..."))
                                except Alias.DoesNotExist:
                                    self.stdout.write(self.style.SUCCESS(f"> Alias: {alias_name} created"))
                                    Alias.objects.create(name=alias_name, ref_type=ref_type)
                        
                        try:
                            first_href = char_data.get("first_href")
                            if first_href is not None:
                                try:
                                    endpoint = first_href.split(".com")[1]
                                except IndexError:
                                    # Failed to split URL on `.com` meaning the href was likely
                                    # a relative link to another wiki page
                                    first_ref = None
                                else:
                                    first_ref = Chapter.objects.get(
                                        # Account for existance or lack of "/" at end of the URI
                                        Q(source_url__contains=endpoint) | Q(source_url__contains=endpoint + "/") | Q(source_url__contains=endpoint[:-1]))
                            else:
                                first_ref = None
                        except Chapter.DoesNotExist:
                            first_ref = None
                        new_character, new_char_created = Character.objects.get_or_create(
                            ref_type=ref_type,
                            first_chapter_ref=first_ref,
                            wiki_uri=char_data.get("wiki_href"),
                            status=Character.parse_status_str(char_data.get("status")),
                            species=Character.parse_species_str(char_data.get("species"))
                        )
                        if new_char_created:
                            self.stdout.write(self.style.SUCCESS(f"> Character data: {name} created"))
                        else:
                            self.stdout.write(self.style.WARNING(f"> Character data: {name} already exists. Skipping creation..."))

        # Populate locations from wiki data
        if not options.get("skip_wiki_locs"):
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
                                self.style.WARNING(f"> Location RefType: {loc_name} already exists. Skipping creation..."))


        def detect_textref_color(text_ref) -> str | None:
            # Detect TextRef color
            if 'span style="color:' in text_ref.context:
                try:
                    print(f"Found color span in '{text_ref.context}'")
                    i: int = text_ref.context.index("color:")
                    try:
                        rgb_hex: str = text_ref.context[i+text_ref.context[i:].index("#")+1:i+text_ref.context[i:].index(">") - 1].upper()
                    except ValueError:
                        self.stdout.write("Color span found but colored text is outside the current context range.")
                        return None
                    matching_colors: QuerySet = Color.objects.filter(rgb=rgb_hex)
                    if len(matching_colors) == 1:
                        return matching_colors[0]
                    else:
                        if options.get("skip_textref_color_select"):
                            self.stdout.write(
                                self.style.WARNING(f"> TextRef color selection disabled. Skipping {ref_type.name}..."))
                            return None

                        self.stdout.write(f"Unable to automatically select color for TextRef: {text_ref}")
                        sel: int = 0
                        for i, col in enumerate(matching_colors):
                            self.stdout.write(f"{i}: {col}")
                        skip = False
                        while True:
                            try:
                                sel = prompt("Select color (leave empty to skip): ", options.get("prompt_sound"))
                                if sel.strip() == "":
                                    skip = True
                                    break

                                sel = int(sel)
                            except ValueError:
                                self.stdout.write("Invalid selection. Please try again.")
                                continue
                            else:
                                if sel < len(matching_colors):
                                    break
                                self.stdout.write("Invalid selection. Please try again.")

                        if skip:
                            self.stdout.write(
                                self.style.WARNING(f"> No color selection provided. Skipping {text_ref.text}..."))
                            return None
                            
                        return matching_colors[i]
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


        def populate_chapter(book: Book, src_path: Path, chapter_num: int):
            src_chapter: SrcChapter = SrcChapter(src_path)
            if src_chapter.metadata is None:
                self.stdout.write(self.style.SUCCESS(f"> Missing metadata for Chapter: {src_chapter.title}. Skipping..."))
                return
            
            chapter, ref_type_updated = Chapter.objects.update_or_create(
                number=chapter_num,
                defaults= {
                    "number": chapter_num,
                    "title": src_chapter.title,
                    "book": book,
                    "is_interlude": "interlude" in src_chapter.title.lower(),
                    "source_url": src_chapter.metadata.get("url", ""),
                    "post_date": dt.fromisoformat(src_chapter.metadata.get("pub_time", dt.now().isoformat())),
                    "last_update": dt.fromisoformat(src_chapter.metadata.get("mod_time", dt.now().isoformat())),
                    "download_date": dt.fromisoformat(src_chapter.metadata.get("dl_time", dt.now().isoformat())),
                    "word_count": src_chapter.metadata.get("word_count", 0),
                    "authors_note_word_count": src_chapter.metadata.get("authors_note_word_count", 0)
                }
            )

            if ref_type_updated:
                self.stdout.write(self.style.SUCCESS(f"> Chapter created: {chapter}"))
            else:
                self.stdout.write(self.style.WARNING(
                    f"> Chapter \"{src_chapter.title}\" already exists. Chapter updated."))

            if options.get("skip_text_refs"):
                return

            # Populate TextRefs
            character_names = itertools.chain(*[
                [char.ref_type.name, *[alias.name for alias in Alias.objects.filter(ref_type=char.ref_type)]] 
                for char in Character.objects.filter(
                    Q(first_chapter_ref__number__lte=chapter_num) | Q(first_chapter_ref=None))
            ])
            location_names = [x.name for x in RefType.objects.filter(type=RefType.LOCATION)]
            names=itertools.chain(character_names, location_names)
            for text_ref in src_chapter.gen_text_refs(names=names):
                print(f"{chapter.number} - {text_ref}")

                # Check for existing TextRef
                try:
                    TextRef.objects.get(
                        text=text_ref.text,
                        chapter=chapter,
                        line_number=text_ref.line_number,
                        start_column=text_ref.start_column,
                        end_column = text_ref.end_column,
                        context_offset = text_ref.context_offset,
                    )
                    self.stdout.write(self.style.WARNING(f"> TextRef already exists. Skipping..."))
                    continue
                except TextRef.DoesNotExist:
                    ref_type = get_or_create_ref_type(text_ref)

                    # RefType creation could not complete or was skipped
                    if ref_type is None:
                        continue

                color = detect_textref_color(text_ref)

                # Create TextRef
                text_ref, ref_type_created = TextRef.objects.update_or_create(
                    text=text_ref.text,
                    chapter=chapter,
                    line_number=text_ref.line_number,
                    start_column=text_ref.start_column,
                    end_column = text_ref.end_column,
                    context_offset = text_ref.context_offset,
                    defaults= {
                        "text": text_ref.text,
                        "chapter": chapter,
                        "type": ref_type,
                        "color": color,
                        "line_number": text_ref.line_number,
                        "start_column": text_ref.start_column,
                        "end_column": text_ref.end_column,
                        "context_offset": text_ref.context_offset,
                    }
                )
                if ref_type_created:
                    self.stdout.write(self.style.SUCCESS(f"> TextRef: {text_ref.text} created"))
                else:
                    self.stdout.write(
                        self.style.WARNING(f"> TextRef: {text_ref.text} @line {text_ref.line_number} updated...")
                    )
        
        # Populate individual Chapter by ID number
        def populate_chapter_by_id(chapter_id: int):
            try:
                chapter = Chapter.objects.get(number=chapter_id)
                self.stdout.write(f"\nPopulating chapter data for chapter (id={chapter_id}): {chapter.title} ...")
                chapter_dir = Path(glob(f"./data/*/*/*/{chapter.title}")[0])
                populate_chapter(chapter.book, chapter_dir, chapter_id)
            except Chapter.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"> Chapter (id) {chapter_id} does not exist in database. Skipping...")
                )
            except IndexError:
                self.stdout.write(
                    self.style.WARNING(f"> Chapter (id): {chapter_id} source file does not exist. Skipping...")
                )
            return

        chapter_id = options.get("chapter_id")
        if chapter_id is not None:
            populate_chapter_by_id(chapter_id)
            return

        chapter_id_range = options.get("chapter_id_range")
        if chapter_id_range is not None:
            try:
                start, end = [int(x) for x in chapter_id_range.split(",")]
            except ValueError as exc:
                raise CommandError(f"Invalid chapter ID range provided: {chapter_id_range}.") from exc

            for i in range(start, end):
                populate_chapter_by_id(i)

            return


        # Populate Volumes
        self.stdout.write("\nPopulating chapter data by volume...")
        vol_root = Path(options["data_path"], "volumes")
        meta_path = Path(vol_root)
        volumes_metadata = get_metadata(meta_path)
        volumes = sorted(list(volumes_metadata["volumes"].items()), key=lambda x: x[1])

        chapter_num = 0
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
                for chapter_title in src_book.chapters:
                    path = Path(src_book.path, chapter_title)
                    populate_chapter(book, path, chapter_num)
                    chapter_num += 1