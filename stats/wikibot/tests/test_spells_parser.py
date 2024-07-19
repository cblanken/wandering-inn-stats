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
    ).get("aliases") == None


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


def test_strip_tier_ref_tags():
    """Removes any <ref> tags from parsed 'tier' property"""
    assert (
        SpellTableParser.parse_row(
            [
                "[Disintegrate]<br />[Disintegration]",
                "6<ref>[https://wanderinginn.com/2022/03/27/8-76-b/ Chapter 8.76 B]</ref>",
                "",
                "",
                None,
            ]
        ).get("tier")
    ) == "6"
