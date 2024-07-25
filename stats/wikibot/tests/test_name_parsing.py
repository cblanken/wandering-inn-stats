from stats.wikibot.parse import parse_name_field


def test_nowiki_tags():
    """Parses out <nowiki> tags"""
    assert (
        parse_name_field(
            "<nowiki>[</nowiki>[[Beast Tamers|Beast Tamer]]<nowiki>]</nowiki>"
        ).get("name")
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
    assert parsed_fields.get("category") == "Name"

    # Category at end
    parsed_fields = parse_name_field("[Abler Bodied Animals (Ants)]")
    assert parsed_fields.get("name") == "Abler Bodied Animals"
    assert parsed_fields.get("category") == "Ants"

    # Category at end with extra whitespace
    parsed_fields = parse_name_field(
        "[Abler Bodied Animals          (Ants)            ]"
    )
    assert parsed_fields.get("name") == "Abler Bodied Animals"
    assert parsed_fields.get("category") == "Ants"


def test_category_stripped_of_markdown():
    """Parses wikitext markdown removed from 'category'"""
    parsed_fields = parse_name_field("[Alter Ego]<br />[Alter Ego: (''Person'')]")
    assert parsed_fields.get("name") == "Alter Ego"
    assert parsed_fields.get("category") == "Person"


def test_normalized_apostrophe():
    """Normalizes apostrophe (') in names/aliases to (\u2019) which is used by the author in name and alias fields"""
    parsed_fields = parse_name_field("[Bird's Eye View] / [Bird's-Eye View]")
    assert parsed_fields.get("name") == "Bird\u2019s Eye View"
    assert parsed_fields.get("aliases") == ["Bird\u2019s-Eye View"]


def test_parens_not_category():
    """Does not remove internal parens which are part of the name"""
    parsed_fields = parse_name_field("[Break a (Fake) Leg]")
    assert parsed_fields.get("name") == "Break a (Fake) Leg"


def test_parens_not_category():
    """Does not remove internal parens which are part of the name"""
    parsed_fields = parse_name_field("[Break a (Fake) Leg]")
    assert parsed_fields.get("name") == "Break a (Fake) Leg"
    "[(Name): Basic Training]"
