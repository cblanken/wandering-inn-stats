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


def test_category_removed_and_consumes_surrounding_space():
    """Parses out categories in parens "()" including surrounding whitespace"""
    parsed_fields = parse_name_field("[Abler Bodied Animals (Ants)]")
    assert parsed_fields.get("name") == "Abler Bodied Animals"
    assert parsed_fields.get("category") == "Ants"

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
