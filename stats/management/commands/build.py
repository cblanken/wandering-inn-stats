from datetime import datetime as dt
from glob import glob
import itertools
import json
from pathlib import Path
import regex
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.db.models.query import QuerySet
from django.db.utils import DataError, IntegrityError
from django.utils.html import strip_tags
from stats.models import (
    ChapterLine,
    Color,
    ColorCategory,
    Chapter,
    Book,
    Volume,
    TextRef,
    RefType,
    Alias,
    Character,
    Location,
)
from processing import (
    Volume as SrcVolume,
    Book as SrcBook,
    Chapter as SrcChapter,
    TextRef as SrcTextRef,
    Pattern,
    get_metadata,
)

from stats.build_utils import (
    build_reftype_pattern,
    compile_textref_patterns,
    prompt,
    select_ref_type,
    select_ref_type_from_qs,
    COLOR_CATEGORY,
    COLORS,
)


class Command(BaseCommand):
    """Database build command"""

    help = "Update database from chapter source HTML and other metadata files"

    def add_arguments(self, parser):
        parser.add_argument(
            "data_path",
            type=str,
            help="Path in file system where build data is saved to disk. \
                This includes volumes, books, chapters, characters, etc.",
        )
        parser.add_argument(
            "--config-dir",
            type=str,
            default="config",
            help="Directory in file system where config files are saved to \
                    disk. This includes disambiguation.cfg, ...",
        )
        parser.add_argument(
            "-i",
            "--ignore-missing-chapter-metadata",
            action="store_true",
            help="Update Chapter data with defaults if the metadata file \
                    can't be read",
        )
        parser.add_argument(
            "--custom-refs",
            type=str,
            help="Path to a text file containing names of RefTypes to check \
                    instead of checking every existing RefType already \
                    available in the database",
        )
        parser.add_argument(
            "--skip-text-refs",
            action="store_true",
            help="Skip TextRef generation for each Chapter",
        )
        parser.add_argument(
            "--skip-ref-chars",
            action="store_true",
            help="Skip Character TextRef checks",
        )
        parser.add_argument(
            "--skip-ref-locs",
            action="store_true",
            help="Skip Location TextRef checks",
        )
        parser.add_argument(
            "--skip-wiki-chars",
            action="store_true",
            help="Skip Character wiki data build section",
        )
        parser.add_argument(
            "--skip-wiki-spells",
            action="store_true",
            help="Skip [Spell] wiki data build section",
        )
        parser.add_argument(
            "--skip-wiki-classes",
            action="store_true",
            help="Skip [Class] wiki data build section",
        )
        parser.add_argument(
            "--skip-wiki-skills",
            action="store_true",
            help="Skip [Skill] wiki data build section",
        )
        parser.add_argument(
            "--skip-wiki-locs",
            action="store_true",
            help="Skip location wiki data build section",
        )
        parser.add_argument(
            "--skip-wiki-all",
            action="store_true",
            help="Skip all wiki data build sections",
        )
        parser.add_argument(
            "--skip-colors",
            action="store_true",
            help="Skip staticly defined Colors and ColorCategories",
        )
        parser.add_argument(
            "--skip-reftype-select",
            action="store_true",
            help="Skip RefType prompt for unknown RefTypes",
        )
        parser.add_argument(
            "--skip-textref-color-select",
            action="store_true",
            help="Disable TextRef selection prompt for ambiguous TextRef \
                    colors",
        )
        parser.add_argument(
            "--skip-disambiguation",
            action="store_true",
            help="Disable disambiguation checks for TextRefs from \
                    'cfg/disambiguation.cfg'",
        )
        parser.add_argument(
            "--prompt-sound",
            action="store_true",
            help="Play short alert sound when build stops with a user prompt",
        )
        parser.add_argument(
            "--chapter-id",
            type=int,
            default=None,
            help="Download a specific chapter by ID number",
        )
        parser.add_argument(
            "--chapter-id-range",
            type=str,
            default=None,
            help="Download a range of chapters by ID number",
        )
        parser.add_argument(
            "--chapter-line-range",
            type=str,
            default=None,
            help="Limit parsing to a range of chapter lines",
        )

    def get_or_create_ref_type(self, options, text_ref: SrcTextRef) -> RefType | None:
        """Check for existing RefType of TextRef and create if necessary"""
        text_ref.text = strip_tags(text_ref.text)
        while True:  # loop for retries from select RefType prompt
            # Ensure textref did not detect a innocuous word from the disambiguation list
            if text_ref.text in options["disambiguation_list"]:
                if options.get("skip_disambiguation"):
                    self.stdout.write(
                        self.style.WARNING(
                            f"> Disambiguation found but check is disabled (--skip-disambiguation). Skipping..."
                        )
                    )
                    return None

                for exception in options["disambiguation_exceptions"]:
                    pattern = regex.compile(exception)
                    if pattern.search(text_ref.line_text):
                        self.stdout.write(
                            self.style.WARNING(
                                f"> {exception} is in disambiguation exceptions list. Skipping..."
                            )
                        )
                        return None

                # Prompt user to continue
                ans = prompt(
                    f'> "{text_ref.text}" matches a name in [DISAMBIGUATION LIST]. Skip (default) TextRef? (y/n): ',
                    sound=options.get("prompt_sound"),
                )

                # Skip by default
                if ans.lower() == "y" or len(ans) == 0:
                    self.stdout.write(
                        self.style.WARNING(f"> {text_ref.text} skipped...")
                    )
                    return None

            try:
                ref_type = RefType.objects.get(name=text_ref.text)

                self.stdout.write(
                    self.style.WARNING(
                        f"> RefType: {text_ref.text} already exists. Skipping creation..."
                    )
                )
                return ref_type
            except RefType.DoesNotExist:
                ref_type = None
            except RefType.MultipleObjectsReturned:
                ref_types = RefType.objects.filter(name=text_ref.text)
                self.stdout.write(
                    self.style.WARNING(
                        f"> Multiple RefType(s) exist for the name: {text_ref.text}..."
                    )
                )
                ref_type = select_ref_type_from_qs(ref_types, sound=True)
                return ref_type

            # Check for existing Alias
            try:
                alias = Alias.objects.get(name=text_ref.text)
                if alias:
                    self.stdout.write(
                        self.style.WARNING(
                            f'> Alias exists for {text_ref.text} already. Reftype="{alias.ref_type.name}". Skipping creation...'
                        )
                    )
                    return alias.ref_type
            except Alias.DoesNotExist:
                pass

            # Check for alternate forms of RefType (titlecase, pluralized, gendered, etc.)
            ref_name = text_ref.text[1:-1] if text_ref.is_bracketed else text_ref.text

            # TODO: ref_name is string?
            candidates = [text_ref.text.title()]
            singular_ref_type_qs = None
            if ref_name.endswith("s"):
                candidates.append(
                    f"[{ref_name[:-1]}]"
                    if text_ref.is_bracketed
                    else ref_name.text[:-1]
                )
            if ref_name.endswith("es"):
                candidates.append(
                    f"[{ref_name[:-2]}]"
                    if text_ref.is_bracketed
                    else ref_name.text[:-2]
                )
            if ref_name.endswith("ies"):
                candidates.append(
                    f"[{ref_name[:-3]}y]"
                    if text_ref.is_bracketed
                    else ref_name.text[:-3]
                )
            if ref_name.endswith("men"):
                candidates.append(
                    f"[{ref_name[:-3]}man]"
                    if text_ref.is_bracketed
                    else ref_name.text[:-3]
                )
            if ref_name.endswith("women"):
                candidates.append(
                    f"[{ref_name[:-5]}woman]"
                    if text_ref.is_bracketed
                    else ref_name.text[:-5]
                )

            for c in candidates:
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
                alias, created = Alias.objects.get_or_create(
                    name=text_ref.text, ref_type=ref_type
                )
                prelude = f"> RefType: {text_ref.text} did not exist, but it is a alternative form of {ref_type.name}. "
                if created:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"{prelude}No existing Alias was found, so one was created."
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"{prelude}An existing Alias was found, so none were created."
                        )
                    )
                return alias.ref_type

            # Could not find existing RefType or Alias or alternate form so
            # intialize type for new RefType

            # Check for [Skill] or [Class] acquisition messages
            skill_obtained_pattern = regex.compile(
                r"^\[Skill.*([Oo]btained|[Ll]earned).*\]$"
            )
            skill_change_pattern = regex.compile(r"^\[Skill [Cc]hange .*[.!]\]$")

            class_obtained_pattern = regex.compile(r"^\[.*Class\W[Oo]btained.*\]$")
            level_up_pattern = regex.compile(r"^\[.*[Ll]evel \d{1,2}.*[.!]\]$")
            class_consolidation_pattern = regex.compile(
                r"^\[Class [Cc]onsolidat.*[.!]\]$"
            )
            class_upgrade_pattern = regex.compile(
                r"^\[Condition[s]? [Mm]et.*[Cc]lass[.!]\]$"
            )

            spell_obtained_pattern = regex.compile(r"^\[Spell.*[Oo]btained.*\]$")

            if skill_obtained_pattern.match(
                text_ref.text
            ) or skill_change_pattern.match(text_ref.text):
                new_type = RefType.SKILL_UPDATE
            elif (
                class_obtained_pattern.match(text_ref.text)
                or level_up_pattern.match(text_ref.text)
                or class_consolidation_pattern.match(text_ref.text)
                or class_upgrade_pattern.match(text_ref.text)
            ):
                new_type = RefType.CLASS_UPDATE
            elif spell_obtained_pattern.match(text_ref.text):
                new_type = RefType.SPELL_UPDATE
            else:
                # Check for any bracketed Character references or Aliases from
                # text messages or message scrolls like
                # For example: [batman]
                if text_ref.is_bracketed:
                    for name in [
                        x.name
                        for x in itertools.chain(
                            *[
                                RefType.objects.filter(type=RefType.CHARACTER),
                                Alias.objects.filter(ref_type__type=RefType.CHARACTER),
                            ]
                        )
                    ]:
                        if text_ref.text[1:-1].lower() == name.lower():
                            return None

                # Prompt user to select TextRef type
                if options.get("skip_reftype_select"):
                    new_type = None
                else:
                    new_type = select_ref_type(sound=options.get("prompt_sound"))
                    if new_type == "retry":
                        continue  # retry RefType acquisition

            # RefType was NOT categorized, so skip
            if new_type is None:
                self.stdout.write(self.style.WARNING(f"> {text_ref.text} skipped..."))
                return None

            # Create RefType
            try:
                new_ref_type = RefType(name=text_ref.text, type=new_type)
                new_ref_type.save()
                self.stdout.write(self.style.SUCCESS(f"> {new_ref_type} created"))
                return new_ref_type
            except IntegrityError as exc:
                self.stdout.write(
                    self.style.WARNING(
                        f"> {strip_tags(text_ref.text)} already exists. Skipping..."
                    )
                )
                return None
            except DataError as exc:
                self.stdout.write(
                    self.style.WARNING(
                        f'Failed to create RefType from {text_ref.text} and with RefType: "{new_type}". {exc}\nSkipping...'
                    )
                )
                return None

    def select_color_from_options(
        self, matching_colors: QuerySet[Color], prompt_sound: bool
    ) -> Color:
        for i, col in enumerate(matching_colors):
            self.stdout.write(f"{i}: {col}")
        skip = False

        sel: str
        index: int
        while True:
            try:
                sel = prompt(
                    "Select color (leave empty to skip): ",
                    prompt_sound,
                )
                if sel.strip() == "":
                    skip = True
                    break

                index = int(sel)
            except ValueError:
                self.stdout.write("Invalid selection. Please try again.")
                continue
            else:
                if index >= 0 and index < len(matching_colors):
                    break
                self.stdout.write("Invalid selection. Please try again.")

        if skip:
            self.stdout.write(
                self.style.WARNING("> No color selection provided. Skipping...")
            )
            return None

        return matching_colors[i]

    def detect_textref_color(self, options, text_ref) -> str | None:
        # Detect TextRef color
        if 'span style="color:' in text_ref.context:
            try:
                print(f"Found color span in '{text_ref.context}'")
                i: int = text_ref.context.index("color:")
                try:
                    rgb_hex: str = (
                        text_ref.context[
                            i
                            + text_ref.context[i:].index("#")
                            + 1 : i
                            + text_ref.context[i:].index(">")
                            - 1
                        ]
                        .strip()
                        .upper()
                        .replace("#", "")
                        .replace(";", "")
                    )
                except ValueError:
                    self.stdout.write(
                        "Color span found but colored text is outside the current context range."
                    )
                    return None

                matching_colors: QuerySet = Color.objects.filter(rgb=rgb_hex)
                if len(matching_colors) == 1:
                    return matching_colors[0]
                else:
                    if options.get("skip_textref_color_select"):
                        self.stdout.write(
                            self.style.WARNING(
                                "> TextRef color selection disabled. Skipping selection."
                            )
                        )
                        return None

                    self.stdout.write(
                        f"Unable to automatically select color for TextRef: {text_ref}"
                    )

                    return self.select_color_from_options(
                        matching_colors, options.get("prompt_sound")
                    )

            except IndexError:
                print("Can't get color. Invalid TextRef context index")
                raise
            except Color.DoesNotExist:
                print("Can't get color. There is no existing Color for rgb={rgb_hex}")
                raise
            except KeyboardInterrupt as exc:
                print("")
                raise CommandError(
                    "Build interrupted with Ctrl-C (Keyboard Interrupt)."
                ) from exc
            except EOFError as exc:
                print("")
                raise CommandError("Build interrupted with Ctrl-D (EOF).") from exc

        return None

    def build_chapter_by_id(self, options, chapter_num: int):
        """Build individual Chapter by ID"""
        try:
            chapter = Chapter.objects.get(number=chapter_num)
            self.stdout.write(
                f"\nPopulating chapter data for existing chapter (id={chapter_num}): {chapter.title} ..."
            )
            chapter_dir = Path(glob(f"./data/*/*/*/{chapter.title}")[0])
            self.build_chapter(
                options,
                chapter.book,
                chapter_dir,
                chapter_num,
            )
        except Chapter.DoesNotExist as exc:
            self.stdout.write(
                self.style.WARNING(
                    f"> Chapter (id) {chapter_num} does not exist in database and cannot be created \
                            with just a chapter number/id. Please run a regular build with \
                            `--skip-text-refs` to build all Chapter records from the available data."
                )
            )
            chapter_dir = Path(glob(f"./data/*/*/*/{chapter.title}")[0])
            self.build_chapter(
                options,
                chapter.book,
                chapter_dir,
                chapter_num,
            )
        except IndexError:
            self.stdout.write(
                self.style.WARNING(
                    f"> Chapter (id): {chapter_num} source file does not exist. Skipping..."
                )
            )
        return

    def build_chapter(
        self,
        options,
        book: Book,
        src_path: Path,
        chapter_num: int,
    ):
        src_chapter: SrcChapter = SrcChapter(src_path)
        if src_chapter.metadata is None:
            self.stdout.write(
                self.style.WARNING(
                    f"> Missing metadata for Chapter: {src_chapter.title}. Skipping..."
                )
            )
            return

        # TODO: Fix this DB call to guarantee it won't create a new chapter
        # if a chapter with the same chapter title or source_url already exists
        # the `number` parameter may change if new chapters are added earlier in the
        # ToC (like for rewrites) or if they are deleted/condensed
        chapter, ref_type_updated = Chapter.objects.update_or_create(
            number=chapter_num,
            defaults={
                "number": chapter_num,
                "title": src_chapter.title,
                "book": book,
                "is_interlude": "interlude" in src_chapter.title.lower(),
                "source_url": src_chapter.metadata.get("url", ""),
                "post_date": dt.fromisoformat(
                    src_chapter.metadata.get("pub_time", dt.now().isoformat())
                ),
                "last_update": dt.fromisoformat(
                    src_chapter.metadata.get("mod_time", dt.now().isoformat())
                ),
                "download_date": dt.fromisoformat(
                    src_chapter.metadata.get("dl_time", dt.now().isoformat())
                ),
                "word_count": src_chapter.metadata.get("word_count", 0),
                "authors_note_word_count": src_chapter.metadata.get(
                    "authors_note_word_count", 0
                ),
            },
        )

        if ref_type_updated:
            self.stdout.write(self.style.SUCCESS(f"> Chapter created: {chapter}"))
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'> Chapter "{src_chapter.title}" already exists. Chapter updated.'
                )
            )

        if options.get("skip_text_refs"):
            return

        compiled_patterns = options.get("custom_refs")
        if compiled_patterns is None:
            # Compile character names for TextRef search
            # NOTE: names and aliases containing a '(' are filtered out to prevent
            # interference when compiling the regex to match TextRefs
            character_patterns = (
                [
                    "|".join(build_reftype_pattern(char))
                    for char in RefType.objects.filter(type=RefType.CHARACTER)
                    if "(" not in char.name
                ]
                if not options.get("skip_ref_chars")
                else []
            )

            # Compile location names for TextRef search
            location_patterns = (
                [
                    "|".join(build_reftype_pattern(loc))
                    for loc in RefType.objects.filter(type=RefType.LOCATION)
                ]
                if not options.get("skip_ref_locs")
                else []
            )

            # Compile item/artifact names for TextRef search
            # TODO: add item/artifact names

            compiled_patterns = compile_textref_patterns(
                patterns=itertools.chain(character_patterns, location_patterns)
            )

        # Build TextRefs
        line_range = options.get("chapter_line_range")
        if line_range is None:
            line_range = range(0, len(src_chapter.lines))
        else:
            try:
                split = line_range.split(",")
                if len(split[-1]) == 0 or split[-1].isspace():
                    start = int(split[0])
                    end = len(src_chapter.lines)
                else:
                    start, end = [int(x) for x in split]

                print(f"start: {start}, end: {end}")
                line_range = range(start, end)
            except ValueError as exc:
                raise CommandError(
                    f"Invalid chapter line range provided: {line_range}"
                ) from exc

        for i in line_range:
            image_tag_pattern = regex.compile(r".*((<a href)|(<img )).*")
            if image_tag_pattern.match(src_chapter.lines[i]):
                self.stdout.write(
                    self.style.WARNING(f"> Line {i} contains an <img> tag. Skipping...")
                )
                continue
            elif src_chapter.lines[i].startswith(r"<div class="):
                self.stdout.write(
                    self.style.WARNING(
                        f"> Line {i} is entry-content <div>. Skipping..."
                    )
                )
                continue
            elif src_chapter.lines[i].strip() == "":
                self.stdout.write(
                    self.style.WARNING(f"> Line {i} is empty. Skipping...")
                )

            # Create ChapterLine if it doesn't already exist
            try:
                chapter_line, created = ChapterLine.objects.get_or_create(
                    chapter=chapter, line_number=i, text=src_chapter.lines[i]
                )
            except IntegrityError:
                self.stdout.write(self.style.WARNING(f"{src_chapter.lines[i]}"))
                response = prompt(
                    f"> An existing chapter line ({i}) in chapter {chapter} was found with different text. Continue? (y/n): ",
                    sound=True,
                )
                if response.strip().lower() == "y":
                    continue
                else:
                    raise CommandError("Build aborted.")

            if created:
                self.stdout.write(self.style.SUCCESS(f"> Creating line {i:>3}..."))

            text_refs = src_chapter.gen_text_refs(
                i,
                extra_patterns=compiled_patterns,
                only_extra_patterns=bool(options.get("custom_refs")),
            )

            for text_ref in text_refs:
                # Check for existing TextRef
                print(f"{chapter.number} - {text_ref}")
                try:
                    TextRef.objects.get(
                        chapter_line=chapter_line,
                        start_column=text_ref.start_column,
                        end_column=text_ref.end_column,
                    )
                    self.stdout.write(
                        self.style.WARNING("> TextRef already exists. Skipping...")
                    )
                    continue
                except TextRef.DoesNotExist:
                    ref_type = self.get_or_create_ref_type(options, text_ref)

                    # RefType creation could not complete or was skipped
                    if ref_type is None:
                        continue
                except KeyboardInterrupt as e:
                    raise e

                color = self.detect_textref_color(options, text_ref)

                # Create TextRef
                text_ref, ref_type_created = TextRef.objects.update_or_create(
                    chapter_line=chapter_line,
                    start_column=text_ref.start_column,
                    end_column=text_ref.end_column,
                    defaults={
                        "chapter_line": chapter_line,
                        "type": ref_type,
                        "color": color,
                        "start_column": text_ref.start_column,
                        "end_column": text_ref.end_column,
                    },
                )
                if ref_type_created:
                    self.stdout.write(
                        self.style.SUCCESS(f"> TextRef: {text_ref.type.name} created")
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"> TextRef: {text_ref.type.name} @line {text_ref.chapter_line.line_number} updated..."
                        )
                    )

    def build_color_categories(self):
        """Build color categories"""
        self.stdout.write("\nPopulating color categories...")
        for cat in COLOR_CATEGORY:
            try:
                category = ColorCategory.objects.get(name=cat.value)
                self.stdout.write(
                    self.style.WARNING(
                        f"> {category} already exists. Skipping creation..."
                    )
                )
            except ColorCategory.DoesNotExist:
                category = ColorCategory(name=cat.value)
                category.save()
                self.stdout.write(
                    self.style.SUCCESS(f"> ColorCategory created: {category}")
                )

    def build_colors(self):
        self.stdout.write("\nPopulating colors...")
        for col in COLORS:
            matching_category = ColorCategory.objects.get(name=col[1].value)
            try:
                color = Color.objects.get(rgb=col[0], category=matching_category)
                self.stdout.write(
                    self.style.WARNING(
                        f"> {color} already exists. Skipping creation..."
                    )
                )
            except Color.DoesNotExist:
                color = Color(rgb=col[0], category=matching_category)
                color.save()
                self.stdout.write(self.style.SUCCESS(f"> Color created: {color}"))

    def build_spells(self, path: Path):
        """Populate spell types from wiki data"""
        self.stdout.write("\nPopulating spell RefType(s)...")
        with open(path, encoding="utf-8") as file:
            for line in file.readlines():
                line_split: list[str] = line.strip().split("|")
                aliases: list[str] = []
                if len(line_split) > 1:
                    # Spell with aliases
                    spell_name, *aliases = line_split
                else:
                    spell_name = line_split[0]

                spell = "[" + spell_name + "]"
                ref_type, ref_type_created = RefType.objects.get_or_create(
                    name=spell, type=RefType.SPELL
                )

                if ref_type_created:
                    self.stdout.write(self.style.SUCCESS(f"> {ref_type} created"))
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"> Spell RefType: {spell} already exists. Skipping creation..."
                        )
                    )

                for alias_name in aliases:
                    alias_name = "[" + alias_name + "]"
                    new_alias, new_alias_created = Alias.objects.get_or_create(
                        name=alias_name, ref_type=ref_type
                    )
                    if new_alias_created:
                        self.stdout.write(
                            self.style.SUCCESS(f"> Alias: {alias_name} created")
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"> Alias: {alias_name} already exists. Skipping creation..."
                            )
                        )

    def build_skills(self, path: Path):
        self.stdout.write("\nPopulating spell RefType(s)...")
        with open(path, encoding="utf-8") as file:
            for line in file.readlines():
                skill, *aliases = ["[" + name + "]" for name in line.strip().split("|")]

                ref_type, ref_type_created = RefType.objects.get_or_create(
                    name=skill, type=RefType.SKILL
                )
                if ref_type_created:
                    self.stdout.write(self.style.SUCCESS(f"> {ref_type} created"))
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"> Skill RefType: {skill} already exists. Skipping creation..."
                        )
                    )

                for alias_name in aliases:
                    new_alias, new_alias_created = Alias.objects.get_or_create(
                        name=alias_name, ref_type=ref_type
                    )
                    if new_alias_created:
                        self.stdout.write(
                            self.style.SUCCESS(f"> Alias: {alias_name} created")
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"> Alias: {alias_name} already exists. Skipping creation..."
                            )
                        )

    def build_characters(self, path: Path):
        # Populate characters from wiki data
        self.stdout.write("\nPopulating character RefType(s)...")
        with open(path, encoding="utf-8") as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                self.stdout.write(
                    self.style.ERROR(f"> Character data ({path}) could not be decoded")
                )
            else:
                for name, char_data in data.items():
                    # Create Character RefType
                    ref_type, ref_type_created = RefType.objects.get_or_create(
                        name=name, type=RefType.CHARACTER
                    )
                    if ref_type_created:
                        self.stdout.write(
                            self.style.SUCCESS(f"> Character RefType: {name} created")
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"> Character RefType: {name} already exists. Skipping creation..."
                            )
                        )

                    # Create alias for Character first name
                    invalid_first_names = [
                        "a",
                        "an",
                        "archer",
                        "armored",
                        "crusader",
                        "demon",
                        "drake",
                        "dullahan",
                        "eater",
                        "elf",
                        "emperor",
                        "first",
                        "flying",
                        "free",
                        "frost",
                        "gnoll",
                        "goblin",
                        "grand",
                        "grass",
                        "half-elf",
                        "halfling",
                        "harpy",
                        "human",
                        "king",
                        "knight",
                        "old",
                        "oldest",
                        "oracle",
                        "purple",
                        "queen",
                        "selphid",
                        "silent",
                        "silver",
                        "the",
                        "twin",
                        "twisted",
                        "yellow",
                        "wyvern",
                    ]
                    name_split = name.strip().split(" ")
                    if (
                        len(name_split) > 0
                        and name_split[0].lower() not in invalid_first_names
                        and name_split[0] != name
                    ):
                        try:
                            Alias.objects.get(name=name_split[0])
                            self.stdout.write(
                                self.style.WARNING(
                                    f"> Alias: {name_split[0]} already exists. Skipping creation..."
                                )
                            )
                        except Alias.DoesNotExist:
                            self.stdout.write(
                                self.style.SUCCESS(f"> Alias: {name_split[0]} created")
                            )
                            Alias.objects.create(name=name_split[0], ref_type=ref_type)

                    # Create aliases from Character wiki metadata
                    aliases = char_data.get("aliases")
                    if aliases is not None:
                        for alias_name in char_data.get("aliases"):
                            try:
                                Alias.objects.get(name=alias_name)
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"> Alias: {alias_name} already exists. Skipping creation..."
                                    )
                                )
                            except Alias.DoesNotExist:
                                self.stdout.write(
                                    self.style.SUCCESS(f"> Alias: {alias_name} created")
                                )
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
                                    Q(source_url__contains=endpoint)
                                    | Q(source_url__contains=endpoint + "/")
                                    | Q(source_url__contains=endpoint[:-1])
                                )
                        else:
                            first_ref = None
                    except Chapter.DoesNotExist:
                        first_ref = None

                    (
                        new_character,
                        new_char_created,
                    ) = Character.objects.get_or_create(
                        ref_type=ref_type,
                        first_chapter_appearance=first_ref,
                        wiki_uri=char_data.get("wiki_href"),
                        status=Character.parse_status_str(char_data.get("status")),
                        species=Character.parse_species_str(char_data.get("species")),
                    )
                    if new_char_created:
                        self.stdout.write(
                            self.style.SUCCESS(f"> Character data: {name} created")
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"> Character data: {name} already exists. Skipping creation..."
                            )
                        )

    def build_classes(self, path: Path):
        # Populate class types from wiki data
        self.stdout.write("\nPopulating class RefType(s)...")
        with open(path, encoding="utf-8") as file:
            for line in file.readlines():
                class_name = "[" + line.strip() + "]"
                ref_type, ref_type_created = RefType.objects.get_or_create(
                    name=class_name, type=RefType.CLASS
                )

                if ref_type_created:
                    self.stdout.write(self.style.SUCCESS(f"> {ref_type} created"))
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"> Class RefType: {class_name} already exists. Skipping creation..."
                        )
                    )

    def build_locations(self, path: Path):
        self.stdout.write("\nPopulating locations RefType(s)...")
        with open(path, encoding="utf-8") as file:
            try:
                loc_data = json.load(file)
            except json.JSONDecodeError:
                self.stdout.write(
                    self.style.ERROR(f"> location data ({path}) could not be decoded")
                )
            else:
                for loc_name, loc_data in loc_data.items():
                    loc_url = loc_data["url"]
                    ref_type, ref_type_created = RefType.objects.get_or_create(
                        name=loc_name, type=RefType.LOCATION, description=loc_url
                    )
                    if ref_type_created:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"> Location RefType: {loc_name} created"
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"> Location RefType: {loc_name} already exists. Skipping creation..."
                            )
                        )

                    (
                        new_location,
                        new_location_created,
                    ) = Location.objects.get_or_create(
                        ref_type=ref_type,
                        wiki_uri=loc_data.get("url"),
                    )
                    if new_location_created:
                        self.stdout.write(
                            self.style.SUCCESS(f"> Location data: {loc_name} created")
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"> Location data: {loc_name} already exists. Skipping creation..."
                            )
                        )

    def read_config_file(self, p: Path) -> list[str] | None:
        if p.exists():
            try:
                with p.open("r", encoding="utf-8") as f:
                    # Lines starting with '#' act as comments
                    return [x.strip() for x in f.readlines() if x[0] != "#"]
            except OSError as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"Could not read disambiguation.cfg config file! {e}"
                    )
                )

                return None

        return None

    def get_custom_compiled_patterns(self, filepath: Path) -> regex.Pattern:
        try:
            if filepath is None:
                filepath = "config/custom-refs.json"
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                found_reftypes = []
                missing_reftypes = []
                for rt_type, names in data.items():
                    for name in names:
                        qs = RefType.objects.filter(Q(type=rt_type) & Q(name=name))
                        if qs.count() == 0:
                            missing_reftypes.append((rt_type, name))
                        elif qs.count() == 1:
                            found_reftypes.append(qs[0])
                        else:
                            raise CommandError(
                                f"The name \n{name}\n provided by the custom ref config file matches multiple RefTypes → {qs}"
                            )

                for qs in found_reftypes:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Type: {qs.type:>3} | Name: "{qs.name}" found → {qs}'
                        )
                    )

                for qs in missing_reftypes:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Type: {qs[0]:>3} | Name: "{qs[1]}" does not exist. Make sure there isn\'t a typo'
                        )
                    )

                if len(missing_reftypes):
                    raise CommandError(
                        "Some reftypes provided in the custom ref config file did not find any existing RefTypes. There are probably some typos. Fix them and try again."
                    )

                patterns = [
                    "|".join(build_reftype_pattern(rt)) for rt in found_reftypes
                ]

                return compile_textref_patterns(patterns=patterns)

        except json.JSONDecodeError as e:
            raise CommandError(
                f'Build error. Unable to parse JSON file: "{filepath}"'
            ) from e
        except OSError as e:
            raise CommandError(
                f'Build error. Unable to open custom ref list file: "{filepath}"'
            ) from e

    def handle(self, *args, **options) -> None:
        try:
            if options.get("skip_wiki_all"):
                options["skip_wiki_chars"] = True
                options["skip_wiki_locs"] = True
                options["skip_wiki_spells"] = True
                options["skip_wiki_classes"] = True
                options["skip_wiki_skills"] = True

            # Check config files
            config_root = Path(options.get("config_dir", "config"))

            # Disambiguation configs
            options["disambiguation_list"] = self.read_config_file(
                Path(config_root, "disambiguation.cfg")
            )
            options["disambiguation_exceptions"] = self.read_config_file(
                Path(config_root, "disambiguation_exceptions.cfg")
            )

            self.stdout.write("Building DB...")

            # Build from static data
            if not options.get("skip_colors"):
                self.build_color_categories()
                self.build_colors()

            # Build wiki data
            if not options.get("skip_wiki_spells"):
                self.build_spells(Path(options["data_path"], "spells.txt"))
            if not options.get("skip_wiki_skills"):
                self.build_skills(Path(options["data_path"], "skills.txt"))
            if not options.get("skip_wiki_chars"):
                self.build_characters(Path(options["data_path"], "characters.json"))
            if not options.get("skip_wiki_classes"):
                self.build_classes(Path(options["data_path"], "classes.txt"))
            if not options.get("skip_wiki_locs"):
                self.build_locations(Path(options["data_path"], "locations.json"))

            # Setup custom reference list override if provided
            custom_refs_path = options.get("custom_refs")
            if custom_refs_path is not None:
                self.stdout.write(
                    f'Loading custom references config file "{custom_refs_path}"'
                )
                options["custom_refs"] = self.get_custom_compiled_patterns(
                    custom_refs_path
                )

            chapter_id = options.get("chapter_id")
            if chapter_id is not None:
                self.build_chapter_by_id(options, chapter_id)
                return

            chapter_id_range = options.get("chapter_id_range")
            if chapter_id_range is not None:
                try:
                    start, end = [int(x) for x in chapter_id_range.split(",")]
                except ValueError as exc:
                    raise CommandError(
                        f"Invalid chapter ID range provided: {chapter_id_range}."
                    ) from exc

                for i in range(start, end):
                    self.build_chapter_by_id(options, i)

                return

            # Build volumes
            self.stdout.write("\nPopulating chapter data by volume...")
            vol_root = Path(options["data_path"], "volumes")
            meta_path = Path(vol_root)
            volumes_metadata = get_metadata(meta_path)
            volumes = sorted(
                list(volumes_metadata["volumes"].items()), key=lambda x: x[1]
            )

            chapter_num = 0
            for vol_title, vol_num in volumes:
                src_vol: SrcVolume = SrcVolume(Path(vol_root, vol_title))
                volume, ref_type_created = Volume.objects.get_or_create(
                    title=src_vol.title, number=vol_num
                )
                if ref_type_created:
                    self.stdout.write(self.style.SUCCESS(f"> Volume created: {volume}"))
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"> Record for {src_vol.title} already exists. Skipping creation..."
                        )
                    )

                # Build books
                for book_num, book_title in enumerate(src_vol.books):
                    src_book: SrcBook = SrcBook(Path(src_vol.path, book_title))
                    book, book_created = Book.objects.get_or_create(
                        title=book_title, number=book_num, volume=volume
                    )
                    if book_created:
                        self.stdout.write(self.style.SUCCESS(f"> Book created: {book}"))
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"> Record for {book_title} already exists. Skipping creation..."
                            )
                        )
                    # Build chapters
                    for chapter_title in src_book.chapters:
                        path = Path(src_book.path, chapter_title)
                        self.build_chapter(options, book, path, chapter_num)
                        chapter_num += 1
        except KeyboardInterrupt as exc:
            raise CommandError("Build stop. Keyboard interrupt received.") from exc
