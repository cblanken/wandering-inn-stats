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
