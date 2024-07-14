import pytest
from stats.wikibot.parse import ArtifactListParser


"""
Aliases
"""


def test_name_with_aliases():
    """Parses artifact name from aliases"""
    assert (
        ArtifactListParser.parse_row(
            [
                "Aegis of Veltras / Shield of House Veltras / Banner of House Veltras<ref>[https://wanderinginn.com/2022/03/16/8-73-r/ Chapter 8.73 R]</ref>"
            ]
        )
    ).get("name") == "Aegis of Veltras"


def test_aliases_with_ref_tag():
    """Parses artifact name with <ref> tag and '/' delimited aliases"""
    assert (
        ArtifactListParser.parse_row(
            [
                "Aegis of Veltras / Shield of House Veltras / Banner of House Veltras<ref>[https://wanderinginn.com/2022/03/16/8-73-r/ Chapter 8.73 R]</ref>"
            ]
        )
    ).get("aliases") == ["Shield of House Veltras", "Banner of House Veltras"]
