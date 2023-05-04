"""Module for processing scraped chapter text"""
from __future__ import annotations
import re
import sys
from collections import OrderedDict
from enum import Enum, Flag, auto
from pathlib import Path
from typing import Generator

DEFAULT_CONTEXT_LEN = 50

class Color(Enum):
    """
    Enum to specify colored text in the book
    """

    # Classes and Skills
    RED_LEVELING = ["FF0000"] # red skills & classes
    RED_SER_RAIM = ["EB0E0E"] # Ser Raim
    RED_FIRE = ["E01D1D"] # Ivolethe fire
    PINK_CHARM = ["FDDBFF", "FFB8FD", "FD78FF", "FB00FF"] # Magnolia Reinhart charm
    YELLOW_DIVINE_TEMP = ["FFD700"] # Divine and temp skills
    GREEN_UNIQUE = ["99CC00"] # Unique skills & classes
    BLUE_CLASS_RESTORATION = ["#99CCFF"] # Class restoration
    BLUE_COLD = ["CCFFFF", "99CCFF", "3366FF"] # Cold-based skills
    BLUE_WATER = ["00CCFF"] # Water-based skills

    # Antinium Colors
    # TODO: add missing Antinium queen colors
    YELLOW_GRAND_QUEEN = ["FFCC00"] # Antinium Grand Queen speech
    GREEN_FLYING_QUEEN = ["99CC00"] # Antinium Flying Queen speech
    PURPLE_SILENT_QUEEN = ["CC99FF"]
    GRAY_SILENT_QUEEN = ["999999"]
    BROWN_TWISTED_QUEEN = ["993300"]

    # Fae
    GREEN_SPRINT_FAE = ["96BE50"]
    BLUE_WINTER_FAE = ["8AE8FF"]

    # Hidden text
    BLACK_INVIS = "0C0E0E"

    NORMAL = "EEEEEE"

OBTAINED_SUFFIX = r".*[Oo]btained.?\]"
class Pattern(Enum):
    """Text matching RE patterns for processing chapter text"""
    ALL_MAGIC_WORDS = re.compile(r"\[(\w\,? ?)+\]")
    SKILL_OBTAINED = re.compile(r"\[[Ss]kill" + OBTAINED_SUFFIX)
    CLASS_OBTAINED = re.compile(r"\[.*[Cc]lass" + OBTAINED_SUFFIX)
    SPELL_OBTAINED = re.compile(r"\[[Ss]pell" + OBTAINED_SUFFIX)

    @classmethod
    def _or(cls, *patterns: Pattern):
        if len(patterns) == 1:
            return patterns[0].value

        new_pattern = re.compile("|".join([p.value.pattern for p in patterns]))
        return new_pattern

    @classmethod
    def _and(cls, *patterns: Pattern):
        # TODO: implement for combining Pattern with AND
        pass

class RefType(Enum):
    """Text reference types"""
    CHARACTER = auto()
    ITEM = auto()
    SKILL = auto()
    CLASS = auto()
    SPELL = auto()
    MIRACLE = auto()
    OBTAINED = auto()

class TextRef:
    """
    A Text Reference to a specified keyword in the text

    Properties:
    - phrase (str): Keyphrase found
    - line (int): Line number in the text
    - start_column (int): Column number of first letter in (phrase) found in the text
    - end_col (int): Column number of last letter in (phrase) found in the text
    - context (str): Contextual text surrounding (phrase)
    - type (RefType): Type of refence such as Characer, Class, Spell etc.
    """
    def __init__(self, text: str, line_text: str, line_id: int, start_column: int,
        end_column: int, context_offset: int = DEFAULT_CONTEXT_LEN) -> TextRef:
        self.text: str = text.strip()
        self.line_number: int = line_id
        self.start_column: int = start_column
        self.end_column: int = end_column
        self.context_offset: str = context_offset
        self.type: RefType = None

        # Construct surrounding context string
        start = max(start_column - context_offset, 0)
        end = min(end_column + context_offset, len(line_text))
        self.context = line_text[start:end].strip()

    def __str__(self):
        return f"Line: {self.line_number:>5}: {self.text:⋅<55}context: {self.context}"

    def classify_text_ref(self):
        """Interactive classification of TextRef type"""
        print(self)
        try:
            sel = input(
                "Classify the above TextRef ([ch]aracter, [it]em, [sk]ill, [cl]ass, [sp]ell, "
                "[mi]racle, [ob]tained, leave blank to skip): "
            )

            while True:
                if sel.strip() == "":
                    print("> TextRef skipped!\n")
                    return None
                if len(sel) < 2:
                    print("Invalid selection.")
                    yes_no = input("Try again (y/n)")
                    if yes_no.lower() == "y":
                        continue
                    return None
                break

            match sel[:2].lower():
                case "ch":
                    self.type = RefType.CHARACTER
                case "it":
                    self.type = RefType.ITEM
                case "sk":
                    self.type = RefType.SKILL
                case "cl":
                    self.type = RefType.CLASS
                case "sp":
                    self.type = RefType.SPELL
                case "mi":
                    self.type = RefType.MIRACLE
                case "ob":
                    self.type = RefType.OBTAINED

            print(f"> classified as {self.type}\n")
            return self
        except KeyboardInterrupt:
            sys.exit()
        except EOFError:
            sys.exit()

class Chapter:
    """Model for chapter as a file
    
    Args:
    - title (str): Chapter title
    - url (str): URL of chapter at wandering.com
    - path (Path): path to HTML file of downloaded chapter
    """
    def __init__(self, title: str, path: Path):
        self.title: str = title
        self.path: Path = path
        self.all_text_refs: Generator = self.gen_chapter_text_refs(Pattern._or(
            Pattern.ALL_MAGIC_WORDS,
            Pattern.SKILL_OBTAINED,
            Pattern.CLASS_OBTAINED,
            Pattern.SPELL_OBTAINED
        ))

    def gen_chapter_text_refs(self, pattern: re.Pattern, context_len: int = DEFAULT_CONTEXT_LEN):
        """Return  TextRef(s) that match the regex for the given regex patterns

        Args:
        - patterns (Patterns): Bitwise combination of Patterns
        """
        with open(self.path, "r", encoding="utf-8") as file:
            lines = file.readlines()

        matches_per_line = [re.finditer(pattern, line) for line in lines]
        for line_number, matches in enumerate(matches_per_line):
            for match in matches:
                yield TextRef(match.group(), match.string, line_number,
                            match.start(), match.end(), context_len)

    def print_all_text_refs(self):
        """Print TextRef(s) for chapter
        """
        headline = f"{self.title} - {self.path}"
        print("")
        print("=" * len(headline))
        print(headline)
        print("=" * len(headline))
        for ref in self.all_text_refs:
            print(ref)

    def __str__(self):
        return f"{self.title}: {self.path}"


class Book:
    """Model for book as a file"""
    def __init__(self, title: str, path: Path):
        self.title = title
        self.path = path
        self.chapter_paths: list[Path] = list(Path(self.path).glob("*.html"))
        self.chapter_paths.sort(
            key=lambda n: f"{''.join([x.split('_')[0] for x in n.parts[1:]]):0>7}")

        self.chapters: OrderedDict[Chapter] = OrderedDict()
        for chapter_path in self.chapter_paths:
            title = chapter_path.stem.split('_')[1]
            self.chapters[title] = Chapter(title, chapter_path)

    def __str__(self):
        return f"{self.title}: {self.path}"

class Volume:
    """Model for Volume as a file"""
    def __init__(self, title: str, path: Path):
        self.title: str = title
        self.path: Path = path
        book_paths: list[Path] = [dir for dir in Path(path).iterdir() if dir.is_dir()]
        self.books: OrderedDict[Book] = OrderedDict()
        for book_path in book_paths:
            assert "Book" in str(book_path)
            title = book_path.name.split('_')[1]
            self.books[title] = Book(title, book_path)

    def print_all_text_refs(self):
        """Print all text references found by `generate_all_text_refs` generator
        """
        for book in self.books:
            for chapter in book.chapters:
                chapter.print_all_text_refs()

    def __str__(self):
        return f"{self.title}: {self.path.absolute()}"
