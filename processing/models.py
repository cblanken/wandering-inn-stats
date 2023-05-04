"""Models for Wandering Inn volume and chapter data
"""
from __future__ import annotations
import sys
from enum import Enum, auto

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
    BLUE_CLASS_RESTORATION = ["#99CCFF"]
    BLUE_COLD = ["CCFFFF", "99CCFF", "3366FF"] # Cold-based skills
    BLUE_WATER = ["00CCFF"] # Water-based skills

    # Antinium Colors
    YELLOW_GRAND_QUEEN = "FFCC00" # Antinium Grand Queen speech
    GREEN_FLYING_QUEEN = "99CC00"
    PURPLE_SILENT_QUEEN = "CC99FF"
    GRAY_SILENT_QUEEN = "999999"
    BROWN_TWISTED_QUEEN = "993300"

    # Fae
    GREEN_SPRINT_FAE = ["96BE50"]
    BLUE_WINTER_FAE = ["8AE8FF"]

    # Hidden text
    BLACK_INVIS = "0C0E0E"

    NORMAL = "EEEEEE"

class RefType(Enum):
    """Text reference types"""
    CHARACTER = "CHARACTER"
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
        return f"Line: {self.line_number}: {self.text:.<55}context: {self.context}"

    def classify_text_ref(self):
        """Interactive classification of TextRef type"""
        print(self)
        try:
            sel = input("Classify the above TextRef ([ch]aracter, [it]em, [sk]ill, [cl]ass, [sp]ell, [mi]racle, [ob]tained): ")

            while True:
                if sel.strip() == "":
                    print("> TextRef skipped!\n")
                    return
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
        