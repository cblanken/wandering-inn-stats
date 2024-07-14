import pytest
from stats.wikibot.parse import ClassesTableParser


"""
Aliases
"""


def test_no_aliases():
    """Parses table row without any aliases"""
    assert (
        ClassesTableParser.parse_row(
            [
                "[Writer]",
                "[[Andel]], [[Orica]]",
                "scholar/artist class",
                "being an author; otherwise see: [Scribe]",
                "[https://wanderinginn.com/2019/11/12/6-56/ 6.56], [https://wanderinginn.com/2019/12/14/6-63-p/ 6.63 P]",
            ]
        )
    ).get("aliases") == []


def test_aliases_delimited_by_forward_slash():
    """Parses aliases properly when delimited by a forward '/' and whitespace"""
    assert (
        ClassesTableParser.parse_row(
            [
                "[Cameraman] / [Camerawoman] / [Camera Gnoll]",
                "[[Davi]], Kohr",
                "delivery class",
                "unknown, needs a Camera",
                "[https://wanderinginn.com/2020/05/06/7-21-kq/ 7.21 KQ], [https://wanderinginn.com/2021/09/22/8-43/ 8.43], [https://wanderinginn.com/2022/12/25/9-31/ 9.31]",
            ]
        )
    ).get("aliases") == ["[Camerawoman]", "[Camera Gnoll]"]
