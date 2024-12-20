"""Utility functions and classes for build script"""

import asyncio
from asyncio.subprocess import PIPE, STDOUT
from enum import Enum
from pathlib import Path
from pprint import pformat
from subprocess import Popen, TimeoutExpired
import time
from typing import Iterable, Literal, TypeVar, Generic, Sequence
import regex
from django.core.management.base import CommandError
from django.db.models.query import QuerySet
from django.db.models import Model
from processing import Pattern
from stats.models import Alias, RefType
from django.core.management.base import CommandError


def build_reftype_pattern(ref: RefType):
    """Create an OR'ed regex of a Reftype's name and its aliases"""
    return [
        ref.name,
        *[
            alias.name
            for alias in Alias.objects.filter(ref_type=ref)
            if "(" not in alias.name
        ],
    ]


def compile_textref_patterns(patterns: Iterable[str]) -> regex.Pattern[str] | None:
    # Build patterns for finding TextRefs
    prefix = r"[>\W]"
    suffix = r"[<\W\.\?,!]"
    return Pattern._or(
        [regex.compile(f"{pattern}") for pattern in patterns if "(" not in pattern],
        prefix=prefix,
        suffix=suffix,
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
    SUMMER_FAE = "Summer fae talking"
    WINTER_FAE = "Winter fae talking"
    OTHER_FAE = "Other fae or Oberon"
    CLASS_RESTORATION = "Class restoration / Conviction skill"
    DIVINE_TEMP = "Divine/Temporary skills"
    ERIN_LANDMARK_SKILL = "Erin's landmark skill"
    UNIQUE_SKILL = "Unique skills"
    IVOLETHE_FIRE = "Ivolethe summoning fire"
    COLORED_MAGIC_FIRE = "Magical fire of various colors"
    SER_RAIM = "Ser Raim skill"
    RED = "Red skills and classes"
    RYOKA_MAUDLIN = "Ryoka's guilt/depression"
    RYOKA_HATE = "Ryoka's rage/indignation/self-hate"
    RYOKA_OTHER = "Ryoka's other colored speech"
    DARKNESS = "Darkness / fading light"
    PLAIN = "Normal appearing text to overwrite link text color"
    AUTHORITY_SKILL = "Authority based skills"
    RARE_QUEST = "Rare Quests"
    HEROIC_QUEST = "Heroic Quests"
    MYTHICAL_QUEST = "Mythical Quests"
    OTHER_MAGIC = "Other colors related to magic or spellcasting"
    DRAGON_FIRE = "Dragon fire"
    LIGHT_SKILL = "Light-based or sun skills"
    HERITAGE = "Heritage based skills/classes"
    XRN = "Xrn's various colored speech"
    MEMORY = "Memory based speech e.g. Velan"
    GHOSTS = "Ghosts"


Color = tuple[str, COLOR_CATEGORY]

COLORS: list[Color] = [
    # Ice/water/Ceria
    ("3366FF", COLOR_CATEGORY.CERIA_COLD),
    ("99CCFF", COLOR_CATEGORY.CERIA_COLD),
    ("CCFFFF", COLOR_CATEGORY.CERIA_COLD),
    ("00CCFF", COLOR_CATEGORY.SIREN_WATER),
    # Magnolia
    ("FB00FF", COLOR_CATEGORY.MAGNOLIA_CHARM),
    ("FD78FF", COLOR_CATEGORY.MAGNOLIA_CHARM),
    ("FFB8FD", COLOR_CATEGORY.MAGNOLIA_CHARM),
    ("FDDBFF", COLOR_CATEGORY.MAGNOLIA_CHARM),
    ("FEEDFF", COLOR_CATEGORY.MAGNOLIA_CHARM),
    ("F1A1FF", COLOR_CATEGORY.MAGNOLIA_CHARM),
    ("FF00FF", COLOR_CATEGORY.MAGNOLIA_CHARM),
    ("D5A6BD", COLOR_CATEGORY.MAGNOLIA_CHARM),
    # Antinium
    ("99CC00", COLOR_CATEGORY.FLYING_QUEEN),
    ("993300", COLOR_CATEGORY.TWISTED_QUEEN),
    ("999999", COLOR_CATEGORY.ARMORED_QUEEN),
    ("9E89A7", COLOR_CATEGORY.ARMORED_QUEEN),
    ("CB85E9", COLOR_CATEGORY.ARMORED_QUEEN),
    ("D9D9D9", COLOR_CATEGORY.ARMORED_QUEEN),
    ("CC99FF", COLOR_CATEGORY.SILENT_QUEEN),
    ("FFCC00", COLOR_CATEGORY.GRAND_QUEEN),
    # Xrn
    ("C20000", COLOR_CATEGORY.XRN),
    ("E8D05A", COLOR_CATEGORY.XRN),
    ("2CA7D4", COLOR_CATEGORY.XRN),
    ("BD72D4", COLOR_CATEGORY.XRN),
    ("A3A3A3", COLOR_CATEGORY.XRN),
    ("00FFF7", COLOR_CATEGORY.XRN),
    ("FF4D00", COLOR_CATEGORY.XRN),
    ("FFFFFF", COLOR_CATEGORY.XRN),
    ("99CC00", COLOR_CATEGORY.XRN),
    ("FFFF00", COLOR_CATEGORY.XRN),
    ("C73838", COLOR_CATEGORY.XRN),
    ("95C754", COLOR_CATEGORY.XRN),
    ("5D2299", COLOR_CATEGORY.XRN),
    ("CC99FF", COLOR_CATEGORY.XRN),
    ("FF6600", COLOR_CATEGORY.XRN),
    ("00FF00", COLOR_CATEGORY.XRN),
    ("FF0000", COLOR_CATEGORY.XRN),
    ("FFBF00", COLOR_CATEGORY.XRN),
    ("3366FF", COLOR_CATEGORY.XRN),
    ("FF99CC", COLOR_CATEGORY.XRN),
    ("CCFFFF", COLOR_CATEGORY.XRN),
    ("C800FF", COLOR_CATEGORY.XRN),
    ("76A5AF", COLOR_CATEGORY.XRN),
    # Fae
    ("96BE50", COLOR_CATEGORY.SPRING_FAE),
    ("FFFD73", COLOR_CATEGORY.SUMMER_FAE),
    ("8AE8FF", COLOR_CATEGORY.WINTER_FAE),
    ("9234D1", COLOR_CATEGORY.OTHER_FAE),
    ("DE7A10", COLOR_CATEGORY.OTHER_FAE),
    ("D9F7FF", COLOR_CATEGORY.OTHER_FAE),
    # Bad things
    ("FF0000", COLOR_CATEGORY.RED),
    ("6B0000", COLOR_CATEGORY.RED),
    ("CC0000", COLOR_CATEGORY.RED),
    ("E67A7A", COLOR_CATEGORY.RED),
    ("4D0E03", COLOR_CATEGORY.RED),
    # Special classes/skills
    ("99CCFF", COLOR_CATEGORY.CLASS_RESTORATION),
    ("FFD700", COLOR_CATEGORY.DIVINE_TEMP),
    ("FF9900", COLOR_CATEGORY.ERIN_LANDMARK_SKILL),
    ("99CC00", COLOR_CATEGORY.UNIQUE_SKILL),
    ("CC99FF", COLOR_CATEGORY.AUTHORITY_SKILL),
    # Magic fire
    ("FF3700", COLOR_CATEGORY.DRAGON_FIRE),
    ("E01D1D", COLOR_CATEGORY.IVOLETHE_FIRE),
    ("EB0E0E", COLOR_CATEGORY.SER_RAIM),
    ("FF99CC", COLOR_CATEGORY.COLORED_MAGIC_FIRE),
    ("FF95FF", COLOR_CATEGORY.COLORED_MAGIC_FIRE),
    ("A64D79", COLOR_CATEGORY.COLORED_MAGIC_FIRE),
    ("FFFF99", COLOR_CATEGORY.COLORED_MAGIC_FIRE),
    ("FFCC00", COLOR_CATEGORY.COLORED_MAGIC_FIRE),
    ("FF6600", COLOR_CATEGORY.COLORED_MAGIC_FIRE),
    ("FF0000", COLOR_CATEGORY.COLORED_MAGIC_FIRE),
    ("00FF40", COLOR_CATEGORY.COLORED_MAGIC_FIRE),
    # Other magic
    ("339966", COLOR_CATEGORY.OTHER_MAGIC),
    ("800000", COLOR_CATEGORY.OTHER_MAGIC),
    ("947257", COLOR_CATEGORY.OTHER_MAGIC),
    ("FFCC00", COLOR_CATEGORY.OTHER_MAGIC),
    ("8AE8FF", COLOR_CATEGORY.OTHER_MAGIC),
    ("96BE50", COLOR_CATEGORY.OTHER_MAGIC),
    ("801717", COLOR_CATEGORY.OTHER_MAGIC),
    ("FF0000", COLOR_CATEGORY.OTHER_MAGIC),
    ("00FFFF", COLOR_CATEGORY.OTHER_MAGIC),
    ("00FF00", COLOR_CATEGORY.OTHER_MAGIC),
    ("E99FD0", COLOR_CATEGORY.OTHER_MAGIC),
    ("DFFCAC", COLOR_CATEGORY.OTHER_MAGIC),
    ("FFFF99", COLOR_CATEGORY.LIGHT_SKILL),
    # Ryoka
    ("9FC5E8", COLOR_CATEGORY.RYOKA_MAUDLIN),
    ("EA9999", COLOR_CATEGORY.RYOKA_HATE),
    ("C27BA0", COLOR_CATEGORY.RYOKA_OTHER),
    ("B6D7A8", COLOR_CATEGORY.RYOKA_OTHER),
    ("E69138", COLOR_CATEGORY.RYOKA_OTHER),
    ("F6B26B", COLOR_CATEGORY.RYOKA_OTHER),
    ("99CC00", COLOR_CATEGORY.RYOKA_OTHER),
    ("FF00FF", COLOR_CATEGORY.RYOKA_OTHER),
    ("FF9900", COLOR_CATEGORY.RYOKA_OTHER),
    ("99CCFF", COLOR_CATEGORY.RYOKA_OTHER),
    # Quests
    ("95E094", COLOR_CATEGORY.RARE_QUEST),
    ("F29B68", COLOR_CATEGORY.HEROIC_QUEST),
    ("EB81B", COLOR_CATEGORY.MYTHICAL_QUEST),
    # Other
    ("CBF2F3", COLOR_CATEGORY.HERITAGE),
    ("FFFF99", COLOR_CATEGORY.MEMORY),
    ("BDD2DB", COLOR_CATEGORY.GHOSTS),
    # Darkness
    ("787878", COLOR_CATEGORY.DARKNESS),
    ("575757", COLOR_CATEGORY.DARKNESS),
    ("333333", COLOR_CATEGORY.DARKNESS),
    ("8F8F8F", COLOR_CATEGORY.DARKNESS),
    ("404040", COLOR_CATEGORY.DARKNESS),
    ("0C0E0E", COLOR_CATEGORY.INVISIBLE),
    ("B7B7B7", COLOR_CATEGORY.PLAIN),
]


def match_ref_type(type_str: str) -> Literal[2] | None:
    try:
        matches = list(
            filter(lambda rt: rt[0] == type_str.strip()[:2].upper(), RefType.TYPES)
        )

        # Return matching RefType shortcode from RefType.TYPES
        if matches:
            return matches[0][0]

    except ValueError:
        # No match found
        pass
        return None
    else:
        return None


def play_sound():
    sound_path = Path("stats/sounds/alert.mp3")
    try:
        proc = Popen(["/usr/bin/mpg123", "-q", sound_path])
    except OSError as e:
        print(f"! - Alert sound file {sound_path} could not be played. {e}")
    except TimeoutExpired:
        print("! - Alert sound player timed out")


def prompt(s: str = "", sound: bool = False) -> str:
    if sound:
        play_sound()

    return input(s)


def select_ref_type(sound: bool = False) -> str | None:
    """Interactive classification of TextRef type"""
    try:
        while True:
            sel = prompt(
                f'Classify the above TextRef with\n{pformat(RefType.TYPES)}\nleave blank to skip OR use "r" to retry: ',
                sound,
            )

            if sel.strip().lower() == "r":
                return "retry"  # special case to retry RefType acquisition
            if sel.strip() == "":
                return None  # skip without confirmation

            ref_type = match_ref_type(sel)
            if ref_type is None:
                print("Invalid selection.")
                yes_no = prompt("Try again (y/n): ", sound)
                if yes_no.lower() == "y":
                    continue
                return None  # skip with confirmation

            return ref_type

    except KeyboardInterrupt as exc:
        print("")
        raise CommandError(
            "Build interrupted with Ctrl-C (Keyboard Interrupt)."
        ) from exc
    except EOFError as exc:
        print("")
        raise CommandError("Build interrupted with Ctrl-D (EOF).") from exc


T = TypeVar("T", bound=Model)


def select_item_from_qs(qs: QuerySet[T], sound=False) -> T | None:
    if len(qs) < 2:
        raise ValueError("To select from a Queryset, it cannot be empty")
    try:
        while True:
            for i, record in enumerate(qs):
                print(f"{i}: {record}")

            sel: str = prompt(
                f"Select one of the above records (leave empty to skip): ",
                sound,
            )

            sel = sel.strip()
            try:
                sel_i = int(sel)
            except ValueError:
                sel_i = -1  # invalid selection

            if sel_i >= 0 and sel_i < len(qs):
                return qs[sel_i]
            else:
                print("Invalid selection.")
                yes_no = prompt("Try again (y/n): ", sound)
                if yes_no.lower() == "y":
                    continue
                return None  # skip with confirmation

    except KeyboardInterrupt as exc:
        print("")
        raise CommandError(
            "Build interrupted with Ctrl-C (Keyboard Interrupt)."
        ) from exc
    except EOFError as exc:
        print("")
        raise CommandError("Build interrupted with Ctrl-D (EOF).") from exc


def select_ref_type_from_qs(
    qs: QuerySet[RefType], sound: bool = False
) -> RefType | None:
    """Interactive selection of an existing set of RefType(s)"""
    try:
        while True:
            for i, ref_type in enumerate(qs):
                print(f"{i}: {ref_type.name} - {match_ref_type(ref_type.type)}")

            sel: str = prompt(
                "Select one of the RefType(s) from the above options (leave empty to skip): ",
                sound,
            )

            if sel.strip() == "":
                return None  # skip without confirmation

            try:
                sel_i = int(sel)
            except ValueError:
                sel_i = -1  # invalid selection

            if sel_i >= 0 and sel_i < len(qs):
                return qs[sel_i]
            else:
                print("Invalid selection.")
                yes_no = prompt("Try again (y/n): ", sound)
                if yes_no.lower() == "y":
                    continue
                return None  # skip with confirmation

    except KeyboardInterrupt as exc:
        print("")
        raise CommandError(
            "Build interrupted with Ctrl-C (Keyboard Interrupt)."
        ) from exc
    except EOFError as exc:
        print("")
        raise CommandError("Build interrupted with Ctrl-D (EOF).") from exc
