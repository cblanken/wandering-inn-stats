"""Module for processing scraped chapter text"""
from __future__ import annotations
import re
import sys
from collections import OrderedDict
from enum import Enum, Flag, auto
import json
from pathlib import Path
from typing import Generator

OBTAINED_SUFFIX = r".*[Oo]btained.?\]"


class Pattern:
    """Text matching RE patterns for processing chapter text"""

    ALL_MAGIC_WORDS = re.compile(r"\[(\w\,? ?)+\]")
    SKILL_OBTAINED = re.compile(r"\[[Ss]kill" + OBTAINED_SUFFIX)
    CLASS_OBTAINED = re.compile(r"\[.*[Cc]lass" + OBTAINED_SUFFIX)
    SPELL_OBTAINED = re.compile(r"\[[Ss]pell" + OBTAINED_SUFFIX)

    @staticmethod
    def _or(*patterns: re.Pattern):
        if len(patterns) == 1:
            return patterns[0]

        new_pattern = re.compile("|".join([p.pattern for p in patterns]))
        return new_pattern

    @staticmethod
    def _and(*patterns: Pattern):
        # TODO: implement for combining Pattern with AND
        pass


class TextRef:
    """
    A Text Reference to a specified keyword in the text

    Properties:
    - text (str): text found matching the given regex pattern
    - line_text (str): full line of text given for match
    - line_id (int): Line number in the text
    - start_column (int): Column number of first letter in (phrase) found in the text
    - end_col (int): Column number of last letter in (phrase) found in the text
    - context (str): Contextual text surrounding (phrase)
    """

    def __init__(
        self,
        text: str,
        line_text: str,
        line_id: int,
        start_column: int,
        end_column: int,
        context_len: int,
        is_bracketed: bool = True,
    ) -> TextRef:
        self.text: str = text.strip()
        self.is_bracketed = is_bracketed
        self.line_text = line_text.strip()
        self.line_number: int = line_id
        self.start_column: int = start_column
        self.end_column: int = end_column
        self.context_offset: int = context_len

        # Construct surrounding context string
        start = max(start_column - context_len, 0)
        end = min(end_column + context_len, len(line_text))
        self.context = line_text[start:end].strip()

    def __str__(self):
        return f"Line: {self.line_number:>5}: {self.text:⋅<55}context: {self.context}"


def get_metadata(path: Path, filename: str = "metadata.json") -> dict:
    """Return dictionary of metadata from a JSON file"""
    try:
        with open(Path(path, filename), "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as exc:
        print(f'Metadata file at "{path}" could not be decoded.', file=sys.stderr)
        print("Check for syntax errors.", exc, file=sys.stderr)
        return None
    except ValueError as exc:
        print(f'Metadata file at "{path}" could not be found.', exc, file=sys.stderr)
        return None


class Chapter:
    """Model for chapter as a file

    Args:
        title (str): Chapter title
        path (Path): path to HTML file of downloaded chapter
    """

    def __init__(self, path: Path):
        self.path: Path = path
        self.title: str = path.name

        src_path = Path(path, f"{self.title}.html")
        self.src_path: Path = src_path if src_path.exists() else None

        if src_path.exists():
            with open(self.src_path, "r", encoding="utf-8") as file:
                self.lines = file.readlines()
        else:
            self.lines = []

        txt_path = Path(path, f"{self.title}.txt")
        self.txt_path: Path = txt_path if txt_path.exists() else None

        meta_path = Path(path, "metadata.json")
        self.meta_path: Path = meta_path if meta_path.exists() else None
        self.metadata = get_metadata(self.path) if meta_path.exists() else None

        self.__bracket_pattern = Pattern._or(
            Pattern.ALL_MAGIC_WORDS,
            Pattern.SKILL_OBTAINED,
            Pattern.CLASS_OBTAINED,
            Pattern.SPELL_OBTAINED,
        )
        self.all_bracket_refs: Generator[TextRef] = [
            self.gen_text_refs(i) for i in range(len(self.lines))
        ]

    def gen_text_refs(
        self,
        line_num: int,
        names: any[str] = None,
        context_len: int = 50,
    ) -> Generator[TextRef]:
        """Return  TextRef(s) that match the regex for the given regex patterns
        and other arguments

        Args:
            names (str): iterable of characters, locations, items, etc.

        """
        patterns_by_name = {
            name: Pattern._or(
                re.compile(r"(^|\W|[,.\?!][\W]?)" + name + r"(\W|[,.\?!]\W?)"),
                re.compile(r"(^|\W|[,.\?!][\W]?)" + name.upper() + r"(\W|[,.\?!]\W?)"),
            )
            for name in names
        }

        # Yield any matches for bracketed types
        for match in re.finditer(self.__bracket_pattern, self.lines[line_num]):
            yield TextRef(
                match.group(),
                match.string,
                line_num,
                match.start(),
                match.end(),
                context_len,
            )

        # TODO: selection prompt for aliases with multiple matches
        # or if an alias matches a common word
        if names is not None:
            # Yield any matches for named references such as characters, locations, items, etc.
            for name, pattern in patterns_by_name.items():
                for match in re.finditer(pattern, self.lines[line_num]):
                    yield TextRef(
                        name,
                        self.lines[line_num],
                        line_num,
                        match.start(),
                        match.end(),
                        context_len,
                    )

    def print_bracket_refs(self):
        """Print TextRef(s) for chapter"""
        headline = f"{self.title} - {self.path}"
        print("")
        print("=" * len(headline))
        print(headline)
        print("=" * len(headline))
        for ref in self.all_bracket_refs:
            print(ref)

    def __str__(self):
        return f"{self.title}: {self.path}"


class Book:
    """Model for book as a file"""

    def __init__(self, path: Path):
        self.path = path
        self.metadata = get_metadata(self.path)
        self.title: str = self.metadata["title"]
        self.chapters: list[str] = [
            x[0]
            for x in sorted(list(self.metadata["chapters"].items()), key=lambda x: x[1])
        ]

    def __str__(self):
        return f"{self.title}: {self.path}"


class Volume:
    """Model for Volume as a file"""

    def __init__(self, path: Path):
        self.path: Path = path
        self.metadata = get_metadata(self.path)
        self.title: str = self.metadata["title"]
        self.books: list[str] = [
            x[0]
            for x in sorted(list(self.metadata["books"].items()), key=lambda x: x[1])
        ]

    def print_all_text_refs(self):
        """Print all text references found by `generate_all_text_refs` generator"""
        for book in self.books:
            for chapter in book.chapters:
                chapter.print_all_text_refs()

    def __str__(self):
        return f"{self.title}: {self.path.absolute()}"
