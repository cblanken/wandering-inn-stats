"""Utility functions and classes for build script"""
from enum import Enum
from pathlib import Path
from pprint import pprint
from sys import stderr
from subprocess import run, TimeoutExpired
from typing import Protocol
from django.core.management.base import CommandError
from django.db.models.query import QuerySet
from stats.models import Alias, RefType


class RefTypeHolder(Protocol):
    @property
    def ref_type(self) -> RefType:
        ...


def build_reftype_pattern(ref: RefTypeHolder):
    """Create an OR'ed regex of a Reftype's name and its aliases"""
    return [
        ref.ref_type.name,
        *[
            alias.name
            for alias in Alias.objects.filter(ref_type=ref.ref_type)
            if "(" not in alias.name
        ],
    ]


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
    PLAIN = "Normal appearing text to overwrite link text color"


Color = tuple[str, COLOR_CATEGORY]

COLORS: list[Color] = [
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
    ("333333", COLOR_CATEGORY.DARKNESS),
    ("B7B7B7", COLOR_CATEGORY.PLAIN),
]


def select_color_type(rgb_hex: str) -> Color | None:
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


def match_ref_type(type_str) -> str | None:
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


def prompt(s: str = "", sound: bool = False):
    if sound:
        sound_filepath = Path("stats/sounds/alert.mp3")
        try:
            run(["mpg12", "-q", "--pitch", ".25", sound_filepath], timeout=1)
        except OSError:
            print(f"! - Alert sound file {sound_filepath} could not be played.")
        except TimeoutExpired:
            print("! - Alert sound player timed out", file=stderr)
            pass

    return input(s)


def select_ref_type(sound: bool = False) -> str | None:
    """Interactive classification of TextRef type"""
    try:
        while True:
            sel = prompt(
                f'Classify the above TextRef with {RefType.TYPES} (leave blank to skip OR use "r" to retry): ',
                sound,
            )

            if sel.strip().lower() == "r":
                return "retry"  # special case to retry RefType acquisition
            if sel.strip() == "":
                return None  # skip without confirmation
            if len(sel) < 2:
                print("Invalid selection.")
                yes_no = prompt("Try again (y/n): ", sound)
                if yes_no.lower() == "y":
                    continue
                return None  # skip with confirmation

            ref_type = match_ref_type(sel)
            return ref_type

    except KeyboardInterrupt as exc:
        print("")
        raise CommandError(
            "Build interrupted with Ctrl-C (Keyboard Interrupt)."
        ) from exc
    except EOFError as exc:
        print("")
        raise CommandError("Build interrupted with Ctrl-D (EOF).") from exc


def select_ref_type_from_qs(qs: QuerySet[RefType], sound: bool = False) -> str | None:
    """Interactive selection of an existing set of RefType(s)"""
    try:
        while True:
            for i, ref_type in enumerate(qs):
                print(f"{i}: {ref_type.name} - {match_ref_type(ref_type.type)}")

            sel = prompt(
                f"Select one of the RefType(s) from the above options (leave empty to skip): ",
                sound,
            )

            if sel.strip() == "":
                return None  # skip without confirmation
            try:
                sel = int(sel)
            except ValueError:
                sel = -1  # invalid selection

            if sel >= 0 and sel < len(qs):
                return qs[sel]
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
