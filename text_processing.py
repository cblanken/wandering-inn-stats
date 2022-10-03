from __future__ import annotations
from pathlib import Path
from enum import Enum
import sys
import re

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
        return (f"line: {self.line_id:<6}start: {self.start_column:<5}end: {self.end_column:<5}text: {self.text:50}context: {self.context}")

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
    """
    def __init__(self, id: int, volume_chapter_id: int, title: str, is_interlude: bool, url: str,
        post_date: str) -> Chapter:
        self.id = id
        self.volume_chapter_id = volume_chapter_id
        self.title = title
        self.is_interlude = is_interlude
        self.url = url
        self.post_date = post_date

    def __str__(self):
        return f"id: {self.id}\tvol_chap_id: {self.volume_chapter_id}\t{self.title}"

class Volume:
    """
    Model for Volume objects

    Attributes:
        id (int): Database ID for volume, should correspond to the sequence of volumes
        title (str): Title of the volume, typically Volume X where X matches the ID
        summary (str): Short summary of the volume
    """
    def __init__(self, id: int, title: str, summary: str = ""):
        self.id = id
        self.title = title
        self.summary = summary

    def __str__(self):
        return f"id: {id}\ttitle: {self.title}\tsummary: {self.summary}"

def get_text_refs(pattern: re.Pattern, lines: list[str], context_len: int = DEFAULT_CONTEXT_LEN) -> list[TextRef]:
    """Return list of TextRef(s) for a given regex pattern over [lines] of text
    """
    text_refs = []
    matches_per_line = [re.finditer(pattern, line) for line in lines]
    for line_id, match in enumerate(matches_per_line):
        for m in match:
            text_ref = TextRef(m.group(), m.string, line_id, m.start(), m.end(), context_len)
            text_refs.append(text_ref)
    return text_refs

def print_refs(filepath: Path, include_classes = False, include_skills = False, include_spells = False):
    """Print refs that match the regex patterns for Classes, Skills, or Spells
    """
    with open(filepath, "r", encoding="utf-8") as file:
        lines = file.readlines()

    refs = get_text_refs(ALL_MAGIC_WORDS_RE, lines)
    if len(refs) > 0:
        for ref in refs:
            print(ref)

    refs = get_text_refs(CLASS_OBTAINED_RE, lines)
    if len(refs) > 0 and include_classes:
        print("\nCLASSES OBTAINED:")
        for ref in refs:
            print(ref)

    refs = get_text_refs(SKILL_OBTAINED_RE, lines)
    if len(refs) > 0 and include_skills:
        print("\nSKILLS OBTAINED:")
        for ref in refs:
            print(ref)

    refs = get_text_refs(SPELL_OBTAINED_RE, lines)
    if len(refs) > 0 and include_spells:
        print("\nSPELLS OBTAINED:")
        for ref in refs:
            print(ref)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python parse.py DIRECTORY")
        sys.exit(1)

    chapters_path = Path(sys.argv[1])
    chapter_paths = chapters_path.glob("*-wanderinginn.com-*")
    chapter_paths = sorted({ int(p.name[:p.name.find("-")]):p for p in chapter_paths }.items())
    for (i, chapter) in chapter_paths:
        print("")
        print("=" * len(str(chapter)))
        print(chapter)
        print("=" * len(str(chapter)))
        print_refs(chapter)
