from stats.wikibot.parse import parse_name_field


def test_list_strip_surrounding_whitespace():
    """Parses out surrounding whitespace from items of a wikitext list"""
    name = parse_name_field(" * Ser Dalius ").get("name")
    assert name == "Ser Dalius"


def test_nowiki_tags():
    """Parses out <nowiki> tags"""
    assert (
        parse_name_field("<nowiki>[</nowiki>[[Beast Tamers|Beast Tamer]]<nowiki>]</nowiki>").get("name")
        == "Beast Tamer"
    )


def test_slash_split_without_internal_brackets():
    """Parses field containing an alias delimited by a forward slash '/' without brackets for the surrounding names"""
    parsed_fields = parse_name_field("[Bladesman/Bladeswoman]")
    assert parsed_fields.get("name") == "Bladesman"
    assert parsed_fields.get("aliases") == ["Bladeswoman"]


def test_category_removed_and_consumes_surrounding_space_and_punctuation():
    """
    Parses out categories in parens "()" including surrounding whitespace and punctuation
    The parens should be "at" the start or end for it to be considered a category ignoring brackets
    """
    # Category at start
    parsed_fields = parse_name_field("[(Name): Basic Training]")
    assert parsed_fields.get("name") == "Basic Training"
    assert parsed_fields.get("categories") == ["Name"]

    # Category at end
    parsed_fields = parse_name_field("[Abler Bodied Animals (Ants)]")
    assert parsed_fields.get("name") == "Abler Bodied Animals"
    assert parsed_fields.get("categories") == ["Ants"]

    # Category at end with extra whitespace
    parsed_fields = parse_name_field("[Abler Bodied Animals          (Ants)            ]")
    assert parsed_fields.get("name") == "Abler Bodied Animals"
    assert parsed_fields.get("categories") == ["Ants"]


def test_category_stripped_of_markdown():
    """Parses wikitext markdown removed from 'category'"""
    parsed_fields = parse_name_field("[Alter Ego]<br />[Alter Ego: (''Person'')]")
    assert parsed_fields.get("name") == "Alter Ego"
    assert parsed_fields.get("categories") == ["Person"]


def test_normalized_apostrophe():
    """Normalizes apostrophe (') in names/aliases to (\u2019) which is used by the author in name and alias fields"""
    parsed_fields = parse_name_field("[Bird's Eye View] / [Bird's-Eye View]")
    assert parsed_fields.get("name") == "Bird\u2019s Eye View"
    assert parsed_fields.get("aliases") == ["Bird\u2019s-Eye View"]


def test_parens_not_category():
    """Does not remove internal parens which are part of the name"""
    parsed_fields = parse_name_field("[Break a (Fake) Leg]")
    assert parsed_fields.get("name") == "Break a (Fake) Leg"


def test_citation_link():
    """Parses citation links. Citation link text should not be included in the name field."""
    parsed_fields = parse_name_field(
        "Everfire Shield<ref>[https://wanderinginn.com/2020/02/26/7-10-k/ Chapter 7.10 K]</ref>"
    )
    assert parsed_fields.get("name") == "Everfire Shield"
    assert parsed_fields.get("citations") == ["Chapter 7.10 K"]


def test_citation_link_with_bracketed_name():
    """Parses citation links. Citation link text should not be included in the name field."""
    parsed_fields = parse_name_field(
        '[Flame Scythe]<ref name="6.57">[https://wanderinginn.com/2019/11/16/6-57/ Chapter 6.57]</ref>',
        wrap_brackets=True,
    )
    assert parsed_fields.get("name") == "[Flame Scythe]"
    assert parsed_fields.get("citations") == ["Chapter 6.57"]
