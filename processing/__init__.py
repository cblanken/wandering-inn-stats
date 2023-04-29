"""Module for processing scraped chapter text"""
import sys
import re
from pathlib import Path
from processing.models import DEFAULT_CONTEXT_LEN, TextRef, TableOfContents, Volume

MAGIC_WORD_PATTERN = r"\[(\w\,? ?)+\]"
OBTAINED_PATTERN = r".*[Oo]btained.?\]$"

SKILL_OBTAINED_RE = re.compile(r"^\[[Ss]kill" + OBTAINED_PATTERN)
CLASS_OBTAINED_RE = re.compile(r"\[.*[Cc]lass" + OBTAINED_PATTERN)
SPELL_OBTAINED_RE = re.compile(r"^\[[Ss]pell" + OBTAINED_PATTERN)
ALL_MAGIC_WORDS_RE = re.compile(MAGIC_WORD_PATTERN)

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
    toc = TableOfContents()

    # TODO: replace with dictionary comprehension
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
