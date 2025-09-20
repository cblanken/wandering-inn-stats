import datetime as dt
from enum import Enum
import itertools
import json
from pathlib import Path
import regex
from typing import Any
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db.models import Q, Model
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
    get_metadata,
)

from stats.build_utils import (
    build_reftype_pattern,
    compile_textref_patterns,
    prompt,
    prompt_yes_no,
    PromptResponse,
    select_ref_type,
    select_ref_type_from_qs,
    select_item_from_qs,
    COLOR_CATEGORY,
    COLORS,
)


class LogCat(Enum):
    """Log categories for log message prefixes
    - `INFO`    general information
    - `WARN`    warnings for potential problems or errors
    - `ERROR`     an error occurred
    - `EXISTS`  RefTypes, Aliases, TextRefs etc. that already exist
    - `NEW`     an item was detected that doesn't already exist and may be created
    - `CREATED` operations that successfully created a new model instance
    - `PREFIX`  RefType items that exist as prefixes usually with a trailing "..."
    - `PROMPT`  user prompts
    - `SKIPPED` user initiated skip
    - `BEGIN`   start of a new section
    """

    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    EXISTS = "EXISTS"
    NEW = "NEW"
    CREATED = "CREATED"
    PREFIX = "PREFIX"
    PROMPT = "PROMPT"
    SKIPPED = "SKIP"
    BEGIN = "BEGIN"
    UPDATED = "UPDATE"


class Command(BaseCommand):
    """Database build command"""

    help = "Update database from chapter source HTML and other metadata files"
    prompt_sound: bool = False

    def add_arguments(self, parser: CommandParser) -> None:
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
            "--skip-volumes",
            action="store_true",
            help="Skip Volume, Book, and Chapter building. NOTE: this option will automatically bypass all TextRef building \
                as well, regardless of the setting for --skip-text-refs.",
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

    def log(self, msg: str, category: LogCat) -> None:
        t = dt.datetime.now(tz=dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        match category:
            case LogCat.WARN | LogCat.SKIPPED:
                style = self.style.WARNING
            case LogCat.NEW | LogCat.BEGIN | LogCat.CREATED:
                style = self.style.SUCCESS
            case LogCat.ERROR:
                style = self.style.ERROR
            case _:
                style = lambda x: x

        full_msg = f"{t} {category.value:<10} {style(msg)}"
        self.stdout.write(full_msg)

    def update_prop_prompt(self, obj: Model, new_value: object, prop: str) -> bool:
        """Prompt user to update property and return selected value and confirmation boolean"""
        old_value = getattr(obj, prop)
        differ: bool = old_value != new_value
        if differ:
            self.log(
                f"A difference in the {prop} of {obj}] was found.",
                LogCat.PROMPT,
            )
            print(f"> OLD: {old_value}")
            print(f"> NEW: {new_value}")

            match prompt_yes_no("> Update?"):
                case PromptResponse.YES:
                    return True
                case PromptResponse.NO:
                    return False

        return False

    def edit_field(self, field: str, desc: str | None = None) -> str | None:
        """
        Prompt user to edit given input string `s` or accept the default.
        Returns `None` if this field should be skipped and no actions taken.

        Parameters
        - `s`: field text to be confirmed or edited
        - `desc`: description of field
        """
        self.log(f'Confirming {desc} "{field}"', LogCat.PROMPT)

        match prompt_yes_no(
            f'> Would you like to edit the {desc} "{self.style.WARNING(field)}"?',
            enable_skip=True,
            sound=self.prompt_sound,
        ):
            case PromptResponse.YES:
                name_resp = prompt(
                    f"> Edit {desc}? (default={self.style.WARNING(field)}): ",
                    sound=self.prompt_sound,
                )
                if name_resp.strip() == "":
                    return field

                if field != name_resp:
                    resp = prompt_yes_no(f"> Is {self.style.WARNING(name_resp)} correct? ")
                    match resp:
                        case PromptResponse.YES:
                            return name_resp
                        case PromptResponse.SKIP:
                            return None
                return field
            case PromptResponse.SKIP:
                return None
            case PromptResponse.NO:
                return field

    def get_or_create_alias(self, rt: RefType, alias_name: str) -> Alias | None:
        """Create Alias with name confirmation and logging of success/failure to console"""
        try:
            alias_name = alias_name.strip()
            alias = Alias.objects.get(name=alias_name, ref_type=rt)
            self.log(
                f'Alias: "{alias_name}" already exists for Reftype "{rt.name}"',
                LogCat.EXISTS,
            )
        except Alias.DoesNotExist:
            if new_name := self.edit_field(alias_name, "Alias name"):
                self.log(
                    f'Alias: "{new_name}" to RefType "{rt.name}" created',
                    LogCat.CREATED,
                )
                alias = Alias.objects.create(name=new_name, ref_type=rt)
            else:
                self.log(f"Alias {alias_name} was skipped", LogCat.SKIPPED)
                alias = None

        return alias

    def get_or_create_reftype(self, rt_name: str, rt_type: str) -> RefType | None:
        """
        Get an existing or create a new RefType with name confirmation and logging of success/failure to console or
        links to an existing Alias of the given `rt_name`.
        """
        try:
            rt = RefType.objects.get(name=rt_name, type=rt_type)
            self.log(f'RefType: "{rt_name}" already exists', LogCat.EXISTS)
            return rt
        except RefType.DoesNotExist:
            # Check for a matching Alias
            try:
                alias = Alias.objects.get(name=rt_name, ref_type__type=rt_type)
                self.log(f'RefType: "{rt_name}" already exists as an Alias', LogCat.EXISTS)
                return alias.ref_type
            except Alias.DoesNotExist:
                self.log(
                    f'RefType: "{rt_name} ({rt_type})" doesn\'t exist. Create?',
                    LogCat.PROMPT,
                )
                edited_name = self.edit_field(rt_name, "RefType name")
                if edited_name is None:
                    return None

                rt, rt_created = RefType.objects.get_or_create(name=edited_name, type=rt_type)
                if rt_created:
                    self.log(self.style.SUCCESS(f'RefType: "{rt}" created'), LogCat.CREATED)
                else:
                    self.log(f'RefType: "{edited_name}" already exists', LogCat.EXISTS)
                return rt

    def get_or_create_ref_type_from_text_ref(self, options: dict[str, Any], text_ref: SrcTextRef) -> RefType | None:
        """Check for existing RefType of TextRef and create backing RefType and Aliases as needed"""
        text_ref.text = strip_tags(text_ref.text)
        while True:  # loop for retries from select RefType prompt
            # Ensure textref did not detect a innocuous word from the disambiguation list
            if text_ref.text in options["disambiguation_list"]:
                if options.get("skip_disambiguation"):
                    self.log(
                        "Disambiguation found but check is disabled (--skip-disambiguation).",
                        LogCat.WARN,
                    )
                    return None

                for exception in options["disambiguation_exceptions"]:
                    pattern = regex.compile(exception)
                    if pattern.search(text_ref.line_text):
                        self.log(
                            f"> {exception} is in the disambiguation exceptions list. Skipping...",
                            LogCat.SKIPPED,
                        )
                        return None

                # Prompt user to continue
                ans = prompt_yes_no(
                    f'> "{text_ref.text}" matches a name in [DISAMBIGUATION LIST]. Create RefType anyway?',
                    sound=bool(options.get("prompt_sound")),
                )

                # Skip by default
                match ans:
                    case PromptResponse.NO:
                        self.log(f"{text_ref.text} skipped...", LogCat.SKIPPED)
                        return None

            try:
                ref_type = RefType.objects.get(name=text_ref.text)
                self.log(f"RefType: {text_ref.text} already exists.", LogCat.INFO)
                return ref_type
            except RefType.DoesNotExist:
                ref_type = None
            except RefType.MultipleObjectsReturned:
                ref_types = RefType.objects.filter(name=text_ref.text)
                self.log(
                    f"Multiple RefType(s) exist for the name: {text_ref.text}...",
                    LogCat.WARN,
                )
                return select_ref_type_from_qs(ref_types, sound=True)

            # Check for existing Alias
            try:
                alias = Alias.objects.get(name=text_ref.text)
                if alias:
                    self.log(
                        f'Alias exists for {text_ref.text} already. Reftype="{alias.ref_type.name}". Skipping creation...',
                        LogCat.SKIPPED,
                    )
                    return alias.ref_type
            except Alias.DoesNotExist:
                pass
            except Alias.MultipleObjectsReturned:
                self.log(f'Multiple aliases found for name: "{text_ref.text}"', LogCat.WARN)
                aliases = Alias.objects.filter(name=text_ref.text)
                alias = select_item_from_qs(aliases)
                if alias is not None:
                    return alias.ref_type

            # Check for alternate forms of RefType (titlecase, pluralized, gendered, etc.)
            ref_name = text_ref.text[1:-1] if text_ref.is_bracketed else text_ref.text

            candidates = [text_ref.text.title()]
            singular_ref_type_qs = None
            if ref_name.endswith("s"):
                candidates.append(f"[{ref_name[:-1]}]" if text_ref.is_bracketed else ref_name[:-1])
            if ref_name.endswith("es"):
                candidates.append(f"[{ref_name[:-2]}]" if text_ref.is_bracketed else ref_name[:-2])
            if ref_name.endswith("ies"):
                candidates.append(f"[{ref_name[:-3]}y]" if text_ref.is_bracketed else ref_name[:-3])
            if ref_name.endswith("men"):
                candidates.append(f"[{ref_name[:-3]}man]" if text_ref.is_bracketed else ref_name[:-3])
            if ref_name.endswith("women"):
                candidates.append(f"[{ref_name[:-5]}woman]" if text_ref.is_bracketed else ref_name[:-5])

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
                alias, created = Alias.objects.get_or_create(name=text_ref.text, ref_type=ref_type)
                prelude = f"RefType: {text_ref.text} did not exist, but it is a alternative form of {ref_type.name}. "
                if created:
                    self.log(
                        f"{prelude}No existing Alias was found, so one was created.",
                        LogCat.CREATED,
                    )
                else:
                    self.log(
                        f"{prelude}An existing Alias was found, so none were created.",
                        LogCat.SKIPPED,
                    )
                return alias.ref_type

            # Could not find existing RefType or Alias or alternate form so intialize new RefType

            # Check for [Skill] or [Class] acquisition messages
            skill_obtained_pattern = regex.compile(r"^\[Skill.*([Oo]btained|[Ll]earned).*\]$")
            skill_change_pattern = regex.compile(r"^\[Skill [Cc]hange .*[.!]\]$")

            class_obtained_pattern = regex.compile(r"^\[.*Class\W[Oo]btained.*\]$")
            level_up_pattern = regex.compile(r"^\[.*[Ll]evel \d{1,2}.*[.!]\]$")
            class_consolidation_pattern = regex.compile(r"^\[Class [Cc]onsolidat.*[.!]\]$")
            class_upgrade_pattern = regex.compile(r"^\[Condition[s]? [Mm]et.*[Cc]lass[.!]\]$")

            spell_obtained_pattern = regex.compile(r"^\[Spell.*[Oo]btained.*\]$")

            if skill_obtained_pattern.match(text_ref.text) or skill_change_pattern.match(text_ref.text):
                new_type = RefType.Type.SKILL_UPDATE
            elif (
                class_obtained_pattern.match(text_ref.text)
                or level_up_pattern.match(text_ref.text)
                or class_consolidation_pattern.match(text_ref.text)
                or class_upgrade_pattern.match(text_ref.text)
            ):
                new_type = RefType.Type.CLASS_UPDATE
            elif spell_obtained_pattern.match(text_ref.text):
                new_type = RefType.Type.SPELL_UPDATE
            else:
                # Check for any bracketed Character references or Aliases from
                # text messages or message scrolls like
                # For example: [batman]
                if text_ref.is_bracketed:
                    for name in [
                        x.name
                        for x in itertools.chain(
                            *[
                                RefType.objects.filter(type=RefType.Type.CHARACTER),
                                Alias.objects.filter(ref_type__type=RefType.Type.CHARACTER),
                            ],
                        )
                    ]:
                        if text_ref.text[1:-1].lower() == name.lower():
                            return None

                # Prompt user to select TextRef type
                if options.get("skip_reftype_select"):
                    new_type = None
                else:
                    new_type = select_ref_type(sound=bool(options.get("prompt_sound")))
                    if new_type == "retry":
                        continue  # retry RefType acquisition

            # RefType was NOT categorized, so skip
            if new_type is None:
                self.log(f"{text_ref.text} skipped...", LogCat.SKIPPED)
                return None

            # Create RefType
            try:
                new_ref_type = RefType(name=text_ref.text, type=new_type)
                new_ref_type.save()
                self.log(f"{new_ref_type} created", LogCat.CREATED)
                return new_ref_type
            except IntegrityError:
                self.log(
                    f"{strip_tags(text_ref.text)} already exists. Skipping...",
                    LogCat.SKIPPED,
                )
                return None
            except DataError as exc:
                self.log(
                    f'Failed to create RefType from {text_ref.text} and with RefType: "{new_type}". {exc}',
                    LogCat.SKIPPED,
                )
                return None

    def detect_textref_color(self, options: dict[str, Any], text_ref: SrcTextRef) -> Color | None:
        # Detect TextRef color
        if 'span style="color:' in text_ref.context:
            try:
                print(f"Found color span in '{text_ref.context}'")
                i: int = text_ref.context.index("color:")
                try:
                    rgb_hex: str = (
                        text_ref.context[
                            i + text_ref.context[i:].index("#") + 1 : i + text_ref.context[i:].index(">") - 1
                        ]
                        .strip()
                        .upper()
                        .replace("#", "")
                        .replace(";", "")
                    )
                except ValueError:
                    self.log(
                        "Color span found but colored text is outside the current context range.",
                        LogCat.WARN,
                    )
                    return None

                matching_colors: QuerySet = Color.objects.filter(rgb=rgb_hex)
                if len(matching_colors) == 1:
                    return matching_colors[0]
                if options.get("skip_textref_color_select"):
                    self.log(
                        "TextRef color selection disabled. Skipping selection.",
                        LogCat.SKIPPED,
                    )
                    return None

                self.log(
                    f"Unable to automatically select color for TextRef: {text_ref}",
                    LogCat.PROMPT,
                )

                try:
                    return select_item_from_qs(matching_colors)
                except ValueError:
                    # TODO: add option to create new Color
                    self.log(
                        f'No available Colors match "{rgb_hex}".',
                        LogCat.WARN,
                    )
                    return None

            except IndexError:
                print("Can't get color. Invalid TextRef context index")
                raise
            except Color.DoesNotExist:
                print("Can't get color. There is no existing Color for rgb={rgb_hex}")
                raise
            except KeyboardInterrupt as exc:
                print("")
                msg = "Build interrupted with Ctrl-C (Keyboard Interrupt)."
                raise CommandError(msg) from exc
            except EOFError as exc:
                print("")
                msg = "Build interrupted with Ctrl-D (EOF)."
                raise CommandError(msg) from exc

        return None

    def build_chapter_by_id(self, options: dict[str, Any], chapter_num: int) -> None:
        """Build individual Chapter by ID"""
        try:
            chapter = Chapter.objects.get(number=chapter_num)
            chapter_dir = list(Path.glob(Path("./data"), f"*/*/*/{chapter.title}"))[0]
            self.log(
                f"Populating chapter data for existing chapter (id={chapter_num}): {chapter.title} ...",
                LogCat.INFO,
            )
            self.build_chapter(
                options,
                chapter.book,
                chapter_dir,
                chapter_num,
            )
        except Chapter.DoesNotExist:
            self.log(
                f"Chapter (id) {chapter_num} does not exist in database and cannot be created with just a chapter number/id. Please run a regular build with `--skip-text-refs` to build all Chapter records from the available data.",
                LogCat.WARN,
            )
            self.build_chapter(
                options,
                chapter.book,
                chapter_dir,
                chapter_num,
            )
        except IndexError:
            self.log(
                f"Chapter (id): {chapter_num} source file does not exist. Skipping...",
                LogCat.SKIPPED,
            )
        return

    def build_chapter(
        self,
        options: dict[str, Any],
        book: Book,
        src_path: Path,
        chapter_num: int,
    ) -> None:
        src_chapter: SrcChapter = SrcChapter(src_path)
        if src_chapter.metadata is None:
            self.log(
                f"Missing metadata for Chapter: {src_chapter.title}. Skipping...",
                LogCat.SKIPPED,
            )
            return

        if src_chapter.metadata.get("word_count", 0) < 30:
            msg = f'The length of chapter "{src_chapter.title}" is very short. It may be locked behind a password or be a non-canon chapter.'
            self.log(msg, LogCat.WARN)

        defaults = {
            "number": chapter_num,
            "title": src_chapter.title,
            "book": book,
            "is_interlude": "interlude" in src_chapter.title.lower(),
            "source_url": src_chapter.metadata.get("url", ""),
            "post_date": dt.datetime.fromisoformat(
                src_chapter.metadata.get("pub_time", dt.datetime.now(tz=dt.timezone.utc).isoformat()),
            ),
            "last_update": dt.datetime.fromisoformat(
                src_chapter.metadata.get("mod_time", dt.datetime.now(tz=dt.timezone.utc).isoformat()),
            ),
            "download_date": dt.datetime.fromisoformat(
                src_chapter.metadata.get("dl_time", dt.datetime.now(tz=dt.timezone.utc).isoformat()),
            ),
            "word_count": src_chapter.metadata.get("word_count", 0),
            "authors_note_word_count": src_chapter.metadata.get("authors_note_word_count", 0),
            "digest": src_chapter.metadata.get("digest"),
        }

        try:
            chapter: Chapter = Chapter.objects.get(title=src_chapter.title, number=chapter_num)
            for key, value in defaults.items():
                curr_value = getattr(chapter, key)
                if curr_value is not None and curr_value != value:
                    update_confirmed = self.update_prop_prompt(chapter, value, key)

                    if update_confirmed:
                        setattr(chapter, key, value)
                        chapter.save()
                        self.log(
                            f"Chapter {chapter.title}->{key} was updated from '{curr_value}' to '{value}'",
                            LogCat.UPDATED,
                        )

                    else:
                        self.log(
                            f"{chapter.title}->{key} differs from the new value ({curr_value}) but was not updated",
                            LogCat.INFO,
                        )

                    if update_confirmed and key == "digest":
                        self.log(
                            f"The digest of the contents of chapter: {chapter.title} was changed. This may indicate the TextRefs for chapter {chapter.title} need to be rebuilt.",
                            LogCat.WARN,
                        )

                        match prompt_yes_no(f"Delete all existing TextRefs for chapter {chapter.title}?"):
                            case PromptResponse.YES:
                                TextRef.objects.filter(chapter_line__chapter=chapter).delete()
                                self.log(
                                    f"All TextRefs for chapter {chapter.title} were successfully deleted", LogCat.INFO
                                )

        except Chapter.DoesNotExist:
            chapter = Chapter.objects.create(**defaults)
            self.log(f"Chapter created: {chapter.title}", LogCat.CREATED)
        except IntegrityError as e:
            self.log(
                f'A DB integrity error occurred. Chapter "{src_chapter.title}" could not be created.',
                LogCat.ERROR,
            )
            msg = f"Chapter integrity failed when building a chapter. The indexing of the source chapters may have been changed.\n{e}"
            raise CommandError(msg) from e

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
                    for char in RefType.objects.filter(type=RefType.Type.CHARACTER)
                    if "(" not in char.name
                ]
                if not options.get("skip_ref_chars")
                else []
            )

            # Compile location names for TextRef search
            location_patterns = (
                ["|".join(build_reftype_pattern(loc)) for loc in RefType.objects.filter(type=RefType.Type.LOCATION)]
                if not options.get("skip_ref_locs")
                else []
            )

            # Compile item/artifact names for TextRef search
            # TODO: add item/artifact names

            compiled_patterns = compile_textref_patterns(
                patterns=itertools.chain(character_patterns, location_patterns),
            )

        # Build TextRefs
        line_range = options.get("chapter_line_range")
        if line_range is None:
            line_range = range(len(src_chapter.lines))
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
                msg = f"Invalid chapter line range provided: {line_range}"
                raise CommandError(msg) from exc

        for i in line_range:
            image_tag_pattern = regex.compile(r".*((<a href)|(<img )).*")
            if image_tag_pattern.match(src_chapter.lines[i]):
                self.log(f"Line {i} contains an <img> tag. Skipping...", LogCat.SKIPPED)
                continue
            if src_chapter.lines[i].startswith(r"<div class="):
                self.log(f"Line {i} is an entry-content <div>. Skipping...", LogCat.SKIPPED)
                continue
            if src_chapter.lines[i].strip() == "":
                self.log(f"Line {i} is empty. Skipping...", LogCat.SKIPPED)

            # Create ChapterLine if it doesn't already exist
            try:
                chapter_line, created = ChapterLine.objects.get_or_create(
                    chapter=chapter,
                    line_number=i,
                    text=src_chapter.lines[i],
                )
            except IntegrityError as e:
                self.log(
                    f"An existing chapter line ({i}) in chapter {chapter} was found with different text.",
                    LogCat.PROMPT,
                )

                resp = prompt_yes_no("Continue?", sound=bool(options.get("prompt_sound")))
                if resp:
                    continue

                self.log("Build was aborted", LogCat.ERROR)
                msg = "Build aborted."
                raise CommandError(msg) from e

            if created:
                self.log(f"Created line {i:>3}", LogCat.CREATED)

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
                    self.log("TextRef already exists. Skipping...", LogCat.SKIPPED)
                    continue
                except TextRef.DoesNotExist:
                    ref_type = self.get_or_create_ref_type_from_text_ref(options, text_ref)

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
                    self.log(f"TextRef: {text_ref.type.name} created", LogCat.CREATED)
                else:
                    self.log(
                        f"TextRef: {text_ref.type.name} @line {text_ref.chapter_line.line_number} updated",
                        LogCat.UPDATED,
                    )

    def build_color_categories(self) -> None:
        """Build color categories"""
        self.log("Populating color categories...", LogCat.BEGIN)
        for cat in COLOR_CATEGORY:
            try:
                category = ColorCategory.objects.get(name=cat.value)
                self.log(f"{category} already exists", LogCat.SKIPPED)
            except ColorCategory.DoesNotExist:
                category = ColorCategory(name=cat.value)
                category.save()
                self.log(
                    self.style.SUCCESS(f"ColorCategory created: {category}"),
                    LogCat.CREATED,
                )

    def build_colors(self) -> None:
        self.log("Populating colors...", LogCat.BEGIN)
        for col in COLORS:
            matching_category = ColorCategory.objects.get(name=col[1].value)
            try:
                color = Color.objects.get(rgb=col[0], category=matching_category)
                self.log(f"{color} already exists", LogCat.SKIPPED)
            except Color.DoesNotExist:
                color = Color(rgb=col[0], category=matching_category)
                color.save()
                self.log(self.style.SUCCESS(f"Color created: {color}"), LogCat.CREATED)

    def build_spells(self, path: Path) -> None:
        """Populate spell types from wiki data"""
        self.log("Populating spell RefType(s)...", LogCat.BEGIN)
        with Path.open(path, encoding="utf-8") as file:
            try:
                spell_data = json.load(file)
            except json.JSONDecodeError:
                self.log(f"[Spell] data ({path}) could not be decoded", LogCat.ERROR)
            else:
                for spell_name, values in spell_data.items():
                    if rt := self.get_or_create_reftype(spell_name, RefType.Type.SPELL):
                        if aliases := values.get("aliases"):
                            for alias_name in aliases:
                                self.get_or_create_alias(rt, alias_name)
                    else:
                        self.log(
                            self.style.ERROR(f"RefType {spell_name} was skipped"),
                            LogCat.SKIPPED,
                        )

    def build_skills(self, path: Path) -> None:
        # Populate skills from wiki data
        self.log("Populating skill RefType(s)...", LogCat.BEGIN)
        with Path.open(path, encoding="utf-8") as file:
            try:
                skill_data = json.load(file)
            except json.JSONDecodeError:
                self.log(f"[Skill] data ({path}) could not be decoded", LogCat.ERROR)
            else:
                for skill_name, values in skill_data.items():
                    if rt := self.get_or_create_reftype(skill_name, RefType.Type.SKILL):
                        if aliases := values.get("aliases"):
                            for alias_name in aliases:
                                self.get_or_create_alias(rt, alias_name)
                    else:
                        self.log(
                            self.style.ERROR(f"RefType {skill_name} was skipped"),
                            LogCat.SKIPPED,
                        )

    def build_characters(self, path: Path) -> None:
        # Populate characters from wiki data
        self.log("Populating character RefType(s)...", LogCat.BEGIN)
        with Path.open(path, encoding="utf-8") as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                self.log(
                    self.style.ERROR(f"Character data ({path}) could not be decoded"),
                    LogCat.ERROR,
                )
            else:
                for name, char_data in data.items():
                    # Create Character RefType
                    ref_type = self.get_or_create_reftype(name, RefType.Type.CHARACTER)

                    if ref_type is None:
                        self.log(
                            f"RefType: {name} type={RefType.Type.CHARACTER} was skipped.",
                            LogCat.SKIPPED,
                        )
                        continue

                    # Create alias for Character first name
                    invalid_first_names = [
                        # TODO: these should be a config file
                        "a",
                        "an",
                        "aluminum",
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
                        "high",
                        "human",
                        "king",
                        "knight",
                        "lieutenantold",
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
                        self.get_or_create_alias(ref_type, name_split[0])

                    # Create aliases from Character wiki metadata
                    aliases = char_data.get("aliases")
                    if aliases is not None:
                        for alias_name in char_data.get("aliases"):
                            self.get_or_create_alias(ref_type, alias_name)

                    try:
                        if first_hrefs := char_data.get("first_hrefs"):
                            try:
                                # TODO: handle multiple 'first hrefs' e.g. before and after rewrite
                                endpoint = first_hrefs[0].split(".com")[1]
                            except IndexError:
                                # Failed to split URL on `.com` meaning the href was likely
                                # a relative link to another wiki page
                                self.log(f'The first appearance href(s) for "{name}" could not be parsed', LogCat.WARN)
                                first_ref = None
                            else:
                                first_ref = Chapter.objects.get(
                                    # Account for existence or lack of "/" at end of the URI
                                    Q(source_url__contains=endpoint)
                                    | Q(source_url__contains=endpoint + "/")
                                    | Q(source_url__contains=endpoint[:-1]),
                                )
                        else:
                            first_ref = None
                    except Chapter.DoesNotExist:
                        self.log(f"A chapter matching the URL {endpoint} does not exist", LogCat.WARN)
                        first_ref = None

                    try:
                        new_first_chapter_appearance = first_ref
                        new_wiki_uri = f"https://wiki.wanderinginn.com/{char_data.get('page_url')}"
                        new_status = Character.identify_status(char_data.get("status"))
                        new_species = Character.identify_species(char_data.get("species"))
                        (char, char_created) = Character.objects.get_or_create(ref_type=ref_type)

                        if char_created:
                            char.first_chapter_appearance = new_first_chapter_appearance
                            char.wiki_uri = new_wiki_uri
                            char.status = new_status
                            char.species = new_species
                            char.save()
                            self.log(
                                self.style.SUCCESS(f'Character: "{name}" created'),
                                LogCat.CREATED,
                            )
                        else:
                            self.log(f'Character: "{name}" already exists', LogCat.SKIPPED)

                            if self.update_prop_prompt(char, new_first_chapter_appearance, "first_chapter_appearance"):
                                char.first_chapter_appearance = new_first_chapter_appearance
                                char.save()
                                self.log(f"First Appearance updated to {new_first_chapter_appearance}", LogCat.UPDATED)

                            if self.update_prop_prompt(char, new_wiki_uri, "wiki_uri"):
                                char.wiki_uri = new_wiki_uri
                                char.save()
                                self.log(f"Wiki URI updated to {new_wiki_uri}", LogCat.UPDATED)

                            if self.update_prop_prompt(char, new_status, "status"):
                                char.status = new_status
                                char.save()
                                self.log(f"Status updated to {new_status}", LogCat.UPDATED)

                            if self.update_prop_prompt(char, new_species, "species"):
                                char.species = new_species
                                char.save()
                                self.log(f"Species updated to {new_species}", LogCat.UPDATED)

                    except IntegrityError:
                        print(
                            f"There may have been a change in the Character definition or in the input file format. Unable to create Character for {ref_type}",
                        )

    def build_classes(self, path: Path) -> None:
        # Populate class types from wiki data
        self.log("Populating class RefType(s)...", LogCat.BEGIN)
        with Path.open(path, encoding="utf-8") as file:
            try:
                class_data = json.load(file)
            except json.JSONDecodeError:
                self.log(
                    self.style.ERROR(f"> [Class] data ({path}) could not be decoded"),
                    LogCat.ERROR,
                )
            else:
                for class_name, values in class_data.items():
                    if values.get("is_prefix"):
                        self.log(f'RefType: "{class_name}" is a prefix', LogCat.PREFIX)
                        continue

                    if ref_type := self.get_or_create_reftype(class_name, RefType.Type.CLASS):
                        if aliases := values.get("aliases"):
                            for alias_name in aliases:
                                self.get_or_create_alias(ref_type, alias_name)
                    else:
                        self.log(
                            self.style.ERROR(f"RefType {class_name} was skipped"),
                            LogCat.SKIPPED,
                        )

    def build_locations(self, path: Path) -> None:
        # Populate location types from wiki data
        self.log("Populating location RefType(s)...", LogCat.BEGIN)
        with Path.open(path, encoding="utf-8") as file:
            try:
                loc_data_array = json.load(file)
            except json.JSONDecodeError:
                self.log(
                    self.style.ERROR(f"Location data ({path}) could not be decoded"),
                    LogCat.ERROR,
                )
                return
            else:
                for loc_name, loc_data in loc_data_array.items():
                    if loc_rt := self.get_or_create_reftype(loc_name, RefType.Type.LOCATION):
                        if aliases := loc_data.get("aliases"):
                            for alias_name in aliases:
                                self.get_or_create_alias(loc_rt, alias_name)

                        try:
                            loc = Location.objects.get_or_create(ref_type=loc_rt)
                            self.log(
                                f'Location: "{loc_rt.name}" already exists',
                                LogCat.EXISTS,
                            )
                        except Location.DoesNotExist:
                            loc = Location.objects.create(ref_type=loc_rt)
                            loc.wiki_uri = loc_data.get("url")
                            loc.save()
                            self.log(
                                self.style.SUCCESS(f'Location: "{loc_rt.name}" created'),
                                LogCat.CREATED,
                            )

    def read_config_file(self, p: Path) -> list[str] | None:
        if p.exists():
            try:
                with p.open("r", encoding="utf-8") as f:
                    # Lines starting with '#' act as comments
                    return [x.strip() for x in f.readlines() if x[0] != "#"]
            except OSError as e:
                self.log(f"Could not read disambiguation.cfg config file! {e}", LogCat.ERROR)
                return None

        return None

    def get_custom_compiled_patterns(self, filepath: Path | None = None) -> regex.Pattern:
        try:
            if filepath is None:
                filepath = Path("config/custom-refs.json")
            with Path.open(filepath, "r", encoding="utf-8") as f:
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
                            msg = f"The name \n{name}\n provided by the custom ref config file matches multiple RefTypes → {qs}"
                            raise CommandError(
                                msg,
                            )

                for qs in found_reftypes:
                    self.log(
                        f'Type: {qs.type:>3} | Name: "{qs.name}" found → {qs}',
                        LogCat.INFO,
                    )

                for qs in missing_reftypes:
                    self.log(
                        f'Type: {qs[0]:>3} | Name: "{qs[1]}" does not exist. Make sure there isn\'t a typo',
                        LogCat.WARN,
                    )

                if len(missing_reftypes):
                    msg = "Some reftypes provided in the custom ref config file did not find any existing RefTypes. There are probably some typos. Fix them and try again."
                    raise CommandError(
                        msg,
                    )

                patterns = ["|".join(build_reftype_pattern(rt)) for rt in found_reftypes]

                return compile_textref_patterns(patterns=patterns)

        except json.JSONDecodeError as e:
            msg = f'Build error. Unable to parse JSON file: "{filepath}"'
            raise CommandError(msg) from e
        except OSError as e:
            msg = f'Build error. Unable to open custom ref list file: "{filepath}"'
            raise CommandError(msg) from e

    def handle(self, *_args, **options) -> None:  # noqa: ANN002, ANN003
        self.prompt_sound = bool(options.get("prompt_sound"))
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
            options["disambiguation_list"] = self.read_config_file(Path(config_root, "disambiguation.cfg"))
            options["disambiguation_exceptions"] = self.read_config_file(
                Path(config_root, "disambiguation_exceptions.cfg"),
            )

            self.log("Building DB...", LogCat.INFO)

            # Build from static data
            if not options.get("skip_colors"):
                self.build_color_categories()
                self.build_colors()

            # Build wiki data
            if not options.get("skip_wiki_spells"):
                self.build_spells(Path(options["data_path"], "spells.json"))
            if not options.get("skip_wiki_skills"):
                self.build_skills(Path(options["data_path"], "skills.json"))
            if not options.get("skip_wiki_chars"):
                self.build_characters(Path(options["data_path"], "characters.json"))
            if not options.get("skip_wiki_classes"):
                self.build_classes(Path(options["data_path"], "classes.json"))
            if not options.get("skip_wiki_locs"):
                self.build_locations(Path(options["data_path"], "locations.json"))

            # Setup custom reference list override if provided
            if custom_refs_path := options.get("custom_refs"):
                self.log(
                    f'Loading custom references config file "{custom_refs_path}"',
                    LogCat.INFO,
                )
                options["custom_refs"] = self.get_custom_compiled_patterns(custom_refs_path)

            if chapter_id := options.get("chapter_id") is not None:
                self.build_chapter_by_id(options, chapter_id)
                return

            if chapter_id_range := options.get("chapter_id_range"):
                try:
                    start, end = [int(x) for x in chapter_id_range.split(",")]
                except ValueError as exc:
                    msg = f"Invalid chapter ID range provided: {chapter_id_range}."
                    raise CommandError(msg) from exc

                for i in range(start, end):
                    self.build_chapter_by_id(options, i)

                return

            # Build volumes
            if options.get("skip_volumes"):
                return

            self.log("Populating chapter data by volume...", LogCat.INFO)
            vol_root = Path(options["data_path"], "volumes")
            meta_path = Path(vol_root)
            volumes_metadata = get_metadata(meta_path)
            if volumes_metadata is None:
                msg = "Unable to read top-level volumes metadata file. Exiting..."
                raise CommandError(msg)

            volumes = sorted(volumes_metadata["volumes"].items(), key=lambda x: x[1])

            chapter_num = 0
            for vol_title, vol_num in volumes:
                src_vol: SrcVolume = SrcVolume(Path(vol_root, vol_title))
                if src_vol.metadata is None:
                    msg = f"Unable to read volume ({vol_title}) metadata file. Exiting..."
                    raise CommandError(msg)
                volume, ref_type_created = Volume.objects.get_or_create(title=src_vol.title, number=vol_num)
                if ref_type_created:
                    self.log(f"Volume created: {volume}", LogCat.CREATED)
                else:
                    self.log(
                        f"Record for {src_vol.title} already exists. Skipping creation...",
                        LogCat.SKIPPED,
                    )

                # Build books
                for book_num, book_title in enumerate(src_vol.books):
                    src_book: SrcBook = SrcBook(Path(src_vol.path, book_title))
                    if src_book.metadata is None:
                        msg = f"Unable to read book ({book_title}) metadata file. Exiting..."
                        raise CommandError(msg)
                    book, book_created = Book.objects.get_or_create(number=book_num, volume=volume)
                    book.title = book_title
                    book.save()

                    if book_created:
                        self.log(f"Book created: {book}", LogCat.CREATED)
                    else:
                        self.log(
                            f"Record for {book_title} already exists. Skipped.",
                            LogCat.SKIPPED,
                        )

                    # Build chapters
                    for chapter_title in src_book.chapters:
                        path = Path(src_book.path, chapter_title)
                        self.build_chapter(options, book, path, chapter_num)
                        chapter_num += 1
        except KeyboardInterrupt as exc:
            msg = "Build stop. Keyboard interrupt received."
            raise CommandError(msg) from exc
