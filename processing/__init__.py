"""Module for processing scraped chapter text"""
import re
from collections import OrderedDict
from pathlib import Path
from . models import DEFAULT_CONTEXT_LEN, TextRef

MAGIC_WORD_PATTERN = r"\[(\w\,? ?)+\]"
ALL_MAGIC_WORDS_RE = re.compile(MAGIC_WORD_PATTERN)

OBTAINED_PATTERN = r".*[Oo]btained.?\]$"
SKILL_OBTAINED_RE = re.compile(r"^\[[Ss]kill" + OBTAINED_PATTERN)
CLASS_OBTAINED_RE = re.compile(r"\[.*[Cc]lass" + OBTAINED_PATTERN)
SPELL_OBTAINED_RE = re.compile(r"^\[[Ss]pell" + OBTAINED_PATTERN)

def get_text_refs(pattern: re.Pattern, lines: list[str],
    context_len: int = DEFAULT_CONTEXT_LEN) -> list[TextRef]:
    """Return list of TextRef(s) for a given regex pattern over [lines] of text
    """
    text_refs = []
    matches_per_line = [re.finditer(pattern, line) for line in lines]
    for line_id, matches in enumerate(matches_per_line):
        for match in matches:
            text_ref = TextRef(match.group(), match.string, line_id, match.start(),
                               match.end(), context_len)
            text_refs.append(text_ref)
    return text_refs

def generate_chapter_text_refs(
    filepath: Path,
    include_classes_obtained: bool = False,
    include_skills_obtained: bool = False,
    include_spells_obtained: bool = False):
    """Return  TextRef(s) that match the regex for the [MAGIC_WORDS] and optionally
    obtained [Classes], [Skills], or [Spells]

    Args:
    - filepath (Path): file system path to chapter text file
    """
    with open(filepath, "r", encoding="utf-8") as file:
        lines = file.readlines()

    refs = get_text_refs(ALL_MAGIC_WORDS_RE, lines)
    if len(refs) > 0:
        for ref in refs:
            yield ref

    if include_classes_obtained:
        class_refs = get_text_refs(CLASS_OBTAINED_RE, lines)
        if len(class_refs) > 0:
            refs += class_refs
            for ref in class_refs:
                yield ref

    if include_skills_obtained:
        skill_refs = get_text_refs(SKILL_OBTAINED_RE, lines)
        if len(skill_refs) > 0:
            refs += skill_refs
            for ref in skill_refs:
                yield ref

    if include_spells_obtained:
        spell_refs = get_text_refs(SPELL_OBTAINED_RE, lines)
        if len(spell_refs) > 0:
            refs += spell_refs
            for ref in spell_refs:
                yield ref

def print_chapter_text_refs(chapter_path: Path):
    """Print references for single chapter at `chapters_path`
    """
    print("")
    print("=" * len(str(chapter_path)))
    print(chapter_path)
    print("=" * len(str(chapter_path)))
    for ref in generate_chapter_text_refs(chapter_path, True, True, True):
        print(ref)


def get_text_ref_generators_by_chapter_title(volumes_dir: Path) -> OrderedDict:
    """Print references for all chapters
    """
    chapter_paths: list[Path] = list(Path(volumes_dir).glob("**/*.txt"))
    chapter_paths.sort(key=lambda n: f"{''.join([x.split('_')[0] for x in n.parts[1:]]):0>7}")

    gens_by_chapter = OrderedDict()
    for path in chapter_paths:
         gens_by_chapter[path] = generate_chapter_text_refs(path, True, True, True)
    return gens_by_chapter

def print_all_text_refs(volumes_dir: Path):
    """Print all text references found by `generate_all_text_refs` generator
    """
    for title, generator in get_text_ref_generators_by_chapter_title(volumes_dir).items():
        print("")
        print("=" * len(str(title)))
        print(title)
        print("=" * len(str(title)))
        for ref in generator:
            print(ref)
