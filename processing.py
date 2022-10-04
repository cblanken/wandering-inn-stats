"""Module for processing scraped chapter text"""
from __future__ import annotations
import sys
import re
from enum import Enum
from pathlib import Path
import get
from bs4 import BeautifulSoup

MAGIC_WORD_PATTERN = r"\[(\w\,? ?)+\]"
OBTAINED_PATTERN = r".*[Oo]btained.?\]$"

SKILL_OBTAINED_RE = re.compile(r"^\[[Ss]kill" + OBTAINED_PATTERN)
CLASS_OBTAINED_RE = re.compile(r"\[.*[Cc]lass" + OBTAINED_PATTERN)
SPELL_OBTAINED_RE = re.compile(r"^\[[Ss]pell" + OBTAINED_PATTERN)
ALL_MAGIC_WORDS_RE = re.compile(MAGIC_WORD_PATTERN)

DEFAULT_CONTEXT_LEN = 50

class Color(Enum):
    """
    Enum to specify colored text in the book
    """
    # TODO: replace values with RGB / HEX
    GREY = "grey"
    GREEN = "green"
    RED = "red"
    LIGHT_BLUE = "light blue"
    BLUE = "blue"
    GOLD = "gold"

class Class:
    """
    Model for [Class]es in the book

    Attributes:
        name (str): name of the [Class]
        desc (str): short description of the [Class]
    """
    def __init__(self, name: str, desc: str):
        self.name = name
        self.desc = desc

class Skill:
    """
    Model for [Skill]es in the book

    Attributes:
        name (str): name of the [Skill]
        desc (str): short description of the [Skill]
    """
    def __init__(self, name: str, desc: str, color: Color = Color.GREY):
        self.name = name
        self.desc = desc
        self.color = color

class Spell:
    """
    Model for [Spell]s in the book

    Attributes:
        name (str): name of the [Spell]
        desc (str): short description of the [Spell]
    """
    def __init__(self, name: str, desc: str):
        self.name = name
        self.desc = desc

class TextRef:
    """
    A Text Reference to a specified keyword in a given text

    Attributes:
        phrase (str): Keyphrase found
        line (int): Line number in the text
        start_column (int): Column number of first letter in (phrase) found in the text
        end_col (int): Column number of last letter in (phrase) found in the text
        context (str): Contextual text surrounding (phrase)
    """
    def __init__(self, text: str, line_text: str, line_id: int, start_column: int,
        end_column: int, context_offset: int = DEFAULT_CONTEXT_LEN) -> TextRef:
        self.text = text.strip()
        self.line_id = line_id
        self.start_column = start_column
        self.end_column = end_column
        self.context_offset = context_offset

        # Construct surrounding context string
        start = max(start_column - context_offset, 0)
        end = min(end_column + context_offset, len(line_text))
        self.context = line_text[start:end].strip()

    def __str__(self):
        return f"line: {self.line_id:<6}start: {self.start_column:<5}end: {self.end_column:<5}text: {self.text:.<50}context: {self.context}"

class Chapter:
    """
    Model for chapter objects

    Attributes:
        id (int): id indicating n for range [1, n] for all book chapters
        volume_chapter_id (int): volume specific id number where the origin is based on the first
            chapter of the volume
        title (str): title of the chapter
        is_interlude (bool): whether or not the chapter is an Interlude chapter
            These chapters usually follow side-characters, often specified with the letters of the
            the characters' first names
        url (str): link to chapter web page
    """
    def __init__(self, id: int, title: str, is_interlude: bool, url: str,
        post_date: str) -> Chapter:
        self.id = id
        self.title = title
        self.is_interlude = is_interlude
        self.url = url
        self.post_date = post_date

    def __str__(self):
        return f"id: {self.id}\t{self.title}\t{self.url}"

class Volume:
    """
    Model for Volume objects

    Attributes:
        id (int): Database ID for volume, should correspond to the sequence of volumes
        title (str): Title of the volume, typically Volume X where X matches the ID
        summary (str): Short summary of the volume
    """
    def __init__(self, id: int, title: str, chapter_range: tuple[int, int], summary: str = ""):
        self.id = id
        self.title = title
        self.chapter_range = chapter_range
        self.summary = summary

    def __str__(self):
        return f"id: {self.id:<4}title: {self.title:<12}summary: {self.summary}"

def get_text_refs(pattern: re.Pattern, lines: list[str],
    context_len: int = DEFAULT_CONTEXT_LEN) -> list[TextRef]:
    """Return list of TextRef(s) for a given regex pattern over [lines] of text
    """
    text_refs = []
    matches_per_line = [re.finditer(pattern, line) for line in lines]
    for line_id, match in enumerate(matches_per_line):
        for m in match:
            text_ref = TextRef(m.group(), m.string, line_id, m.start(), m.end(), context_len)
            text_refs.append(text_ref)
    return text_refs

def generate_chapter_text_refs(
    filepath: Path,
    include_classes = False,
    include_skills = False,
    include_spells = False):
    """Return  TextRef(s) that match the regex for the [MAGIC_WORDS] and optionally
    [Classes], [Skills], or [Spells]

    Arguments:
        filepath (Path): file system path to chapter text file
    """
    with open(filepath, "r", encoding="utf-8") as file:
        lines = file.readlines()

    refs = get_text_refs(ALL_MAGIC_WORDS_RE, lines)
    if len(refs) > 0:
        for ref in refs:
            yield ref

    if include_classes:
        class_refs = get_text_refs(CLASS_OBTAINED_RE, lines)
        if len(class_refs) > 0:
            refs += class_refs
            for ref in class_refs:
                yield ref

    if include_skills:
        skill_refs = get_text_refs(SKILL_OBTAINED_RE, lines)
        if len(skill_refs) > 0:
            refs += skill_refs
            for ref in skill_refs:
                yield ref

    if include_spells:
        spell_refs = get_text_refs(SPELL_OBTAINED_RE, lines)
        if len(spell_refs) > 0:
            refs += spell_refs
            for ref in spell_refs:
                yield ref


def generate_all_text_refs(chapters_dir: Path):
    """Print references for all chapters in `chapters_dir`
    """
    chapter_paths = chapters_dir.glob("*-wanderinginn.com-*")
    chapter_paths = sorted({ int(p.name[:p.name.find("-")]):p for p in chapter_paths }.items())
    for (i, path) in chapter_paths:
        yield (path, generate_chapter_text_refs(path, True, True, True))

def print_all_text_refs(chapters_dir: Path):
    """Print all text references found by `generate_all_text_refs` generator
    Delineated by file path
    """

    for ref in generate_all_text_refs(Path(sys.argv[1])):
        path = ref[0]
        generator = ref[1]
        print("")
        print("=" * len(str(path)))
        print(path)
        print("=" * len(str(path)))
        for ref in generator:
            print(ref)

def get_volumes():
    """Return dictionary of Volume(s) by ID
    """
    toc = get.TableOfContents()

    volumes = {}
    for key, vol in toc.volume_data.items():
        volumes[key] = Volume(key, vol[0], vol[1])

    return volumes

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python parse.py DIRECTORY")
        sys.exit(1)

    # TODO add table of contents fallback file
    print_all_text_refs(Path(sys.argv[1]))
    # for (i, path) in chapter_paths:
    #     with open(path, encoding="utf-8") as fp:
    #         soup = BeautifulSoup(fp)
    #     id = int(path[:path.find("-")])
