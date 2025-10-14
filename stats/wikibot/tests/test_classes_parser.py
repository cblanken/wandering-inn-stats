from stats.wikibot.parse import ClassesTableParser

"""
Name
"""


def test_name_with_nowiki():
    """Parses name with <nowiki> tags"""
    assert (
        ClassesTableParser.parse_row(
            [
                "<nowiki>[</nowiki>[[Beast Tamers|Beast Tamer]]<nowiki>]</nowiki>",
                "[[Laken]], [[:Category:Beast Tamers|...]]",
                "creature-control class",
                "basic entry",
                "[https://wanderinginn.com/2017/06/14/2-03-g/ 2.36 G], [https://wanderinginn.com/2020/09/02/7-43-g/ 7.43 G]",
            ],
        )
    ).get("aliases") is None


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
            ],
        )
    ).get("aliases") is None


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
            ],
        )
    ).get("aliases") == ["[Camerawoman]", "[Camera Gnoll]"]


def test_aliases_delimited_by_forward_slash_no_surrounding_space():
    """Parses aliases properly when delimited by a forward '/' and whitespace"""
    assert (
        ClassesTableParser.parse_row(
            [
                "[Autumn Knight]/[Knight of Autumn]",
                "[[Venoriat]], [[Ilm]]",
                "combat class, melee",
                "specialized [Knight]",
                "[https://wanderinginn.com/2019/09/07/6-42-e/ 6.42 E], [https://wanderinginn.com/2021/05/30/8-24/ 8.24]",
            ],
        )
    ).get("aliases") == ["[Knight of Autumn]"]


"""
Prefix
"""


def test_class_prefix_with_space():
    """Parses [Classes] with prefix indicator '...'"""
    assert (
        ClassesTableParser.parse_row(
            [
                "[Acting ...]",
                "Louseg",
                "class attribute",
                "denotes a promotion from necessity; reported for [Admiral], [Captain]",
                "[https://wanderinginn.com/2023/03/29/interlude-the-spitoon/ 9.Spitoon]",
            ],
        )
    ).get("is_prefix")


def test_class_prefix_no_space():
    """Parses [Classes] with prefix indicator '...'"""
    assert (
        ClassesTableParser.parse_row(
            [
                "[Vice...]",
                "[[Barnethei]]",
                "class attribute",
                "class attribute for those working directly below another of the same or derived class. Reported with [Guildmasters], [Innkeepers], [Innkeepers of Spells]",
                "[https://wanderinginn.com/2022/06/28/9-03/ 9.03], [https://wanderinginn.com/2022/07/10/9-05-npr/ 9.05 NPR]",
            ],
        )
    ).get("is_prefix")
