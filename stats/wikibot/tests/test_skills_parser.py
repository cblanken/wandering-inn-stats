from stats.wikibot.parse import SkillTableParser


"""
Aliases
"""


def test_no_aliases():
    """Parses table row without any aliases"""
    assert (
        SkillTableParser.parse_row(
            [
                "[Zweihander Chop]",
                "",
                "[https://wanderinginn.com/2022/08/30/9-12/ 9.12]",
            ],
        )
    ).get("aliases") is None


def test_no_parse_category_as_alias():
    """Does not parse a (Category) as an alias even if it is split by a linebreak <br /> tag"""
    assert (
        SkillTableParser.parse_row(
            [
                "[Adept Haggler]<br/>(Alchemy)",
                "",
                "[https://wanderinginn.com/2023/07/16/9-54-c/ 9.54 C]",
            ],
        )
    ).get("aliases") is None


"""
Category specifications (in name)
"""


def test_parens_category_in_name_with_linebreak():
    """Parses table row without any aliases but with a category wrapped in parens behind a linebreak"""
    assert (
        SkillTableParser.parse_row(
            [
                "[Vague Directive]<br />(Ants)",
                "",
                "[https://wanderinginn.com/2022/02/13/interlude-hectval-pt-2/ Hectval (Pt. 2)]",
            ],
        ).get("categories")
    ) == ["Ants"]


def test_parens_category_in_name_no_linebreak():
    """Parses table row without any aliases but with a category wrapped in parens inside brackets"""
    assert (
        SkillTableParser.parse_row(
            [
                "[Avert Disaster (Verbal)]",
                "Prevents others from saying certain dialogue that will be emotionally devastating for them.",
                "[https://wanderinginn.com/2021/05/30/8-24/ 8.24]",
            ],
        ).get("categories")
    ) == ["Verbal"]
