import pytest
from stats.wikibot.parse import SpellTableParser


"""
Aliases
"""


def test_no_aliases():
    """Parses table row without any aliases"""
    assert (
        SpellTableParser.parse_row(
            ["[Zone of No Transference]", "Unknown", "", "", None]
        )
    ).get("aliases") == []


def test_alias_with_br_and_forward_slash_delimiter():
    """Parses table row with name containing a linebreak '</br>' and forward slash '/' delimiter"""
    assert (
        SpellTableParser.parse_row(
            [
                "[剑圣 – 心火之刃]<br />/ [Sword Saint - Edge of Heart’s Fire]",
                "Unknown",
                "",
                "[https://wanderinginn.com/2021/04/04/interlude-paradigm-shift-pt-2/ Paradigm Shift (Pt. 2)]",
                None,
            ]
        ).get("aliases")
    ) == ["[Sword Saint - Edge of Heart’s Fire]"]


def test_alias_with_br_no_delimiter():
    """Parses table row with name containing a linebreak '</br>' without any other delimiter"""
    assert (
        SpellTableParser.parse_row(
            ["[Wind Blast]<br />[Windblast]", "Unknown", "", "", None]
        ).get("aliases")
    ) == ["[Windblast]"]
