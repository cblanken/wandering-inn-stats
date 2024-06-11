import pytest
from stats.wikibot.parse import CharInfoBoxParser


"""
Aliases
"""


def test_infobox_single_alias():
    """Parses infobox with only a single name into a singleton list"""
    assert CharInfoBoxParser(["aliases=BlackMage"]).parse().get("aliases") == [
        "BlackMage"
    ]


def test_infobox_no_aliases():
    """Parses infobox without any aliases into an empty list"""
    assert CharInfoBoxParser(["aliases="]).parse().get("aliases") == []


def test_infobox_Bird_aliases():
    """
    Properly parses template (with wikitextparser) from Bird page (mwparserfromhell 0.6.6 fails to parse the
    Infobox_character parameters from the template template). Also properly split aliases by newline '\n'
    """
    assert CharInfoBoxParser(
        [
            "affiliation=*[[Liscor's Antinium Hive]]\n*[[The Wandering Inn]]\n*[[Fellowship of the Inn]]",
            'age=2 (almost 3)<ref name="Interlude – Bird" />',
            "aliases=*Little Bird\n*Bird the Hunter\n*Bird the Liar\n*Sky Hunter\n*Bird of the True Antinium of Izril\n*Second Queen of the Free Antinium",
            "caption1=By [[Fanworks/Bobo Plushie|Bobo Plushie]]",
            "first appearance=*[https://wanderinginn.com/2017/02/22/1-42/ Chapter 1.42] (As Individual)\n*[https://wanderinginn.com/2017/03/01/1-44/ Chapter 1.44] (Introduced)",
            "gender=<div class=\"mw-collapsible mw-collapsed\" data-expandtext=\"Show Spoiler\" data-collapsetext=\"Hide Spoiler\">\n*Male (''Volume 1-9'')\n*Female (''Volume 10 - '')</div>",
            "image=Bird the Hunter by Bobo Plushie.PNG",
            "name=Bird",
            "occupation=*Guard\n*Bird Hunting\n*Antinium Queen",
            "residence=[[The Wandering Inn]]",
            "species=[[Antinium]]",
            "status={{Status|Alive (''Resurrected via Rite of Anastases}}",
        ]
    ).parse().get("aliases") == [
        "Little Bird",
        "Bird the Hunter",
        "Bird the Liar",
        "Sky Hunter",
        "Bird of the True Antinium of Izril",
        "Second Queen of the Free Antinium",
    ]


def test_infobox_aliases():
    """
    Parses aliases with linebreaks (<br> or <br/> variations)
    """
    assert CharInfoBoxParser(
        [
            "aliases=Kasigna of the End<br />God/Goddess of Death<br />Goddess of the Afterlife<br />The Three Women in One<br />Three-In-One<br />One-In-Three<br/>The Maiden<br/>The Mother<br/>The Matriarch<br/>Corpsemother<br/>The Final Judge<br/>Kaligma"
        ]
    ).parse().get("aliases") == [
        "Kasigna of the End",
        "God/Goddess of Death",
        "Goddess of the Afterlife",
        "The Three Women in One",
        "Three-In-One",
        "One-In-Three",
        "The Maiden",
        "The Mother",
        "The Matriarch",
        "Corpsemother",
        "The Final Judge",
        "Kaligma",
    ]


def test_infobox_ref_code_in_aliases():
    """
    Strip <ref> codes from aliases
    """
    assert CharInfoBoxParser(
        [
            "aliases=Cara O'Sullivan<br/>\n'Humble Actor'<br/>\nQueen of Pop<br/>\nSiren of Songs<br/>\nBaroness of the Beat<br/>\nSinger of Terandria<br/>\nSinger of Afiele<br/>\nGravesinger of Afiele<br/>\nSid (''Nickname'')<ref name=\"GS1.01\"/>"
        ]
    ).parse().get("aliases") == [
        "Cara O'Sullivan",
        "'Humble Actor'",
        "Queen of Pop",
        "Siren of Songs",
        "Baroness of the Beat",
        "Singer of Terandria",
        "Singer of Afiele",
        "Gravesinger of Afiele",
        "Sid (Nickname)",
    ]


"""
First appearance / first_href
"""


def test_infobox_no_first_appearance():
    """Parses infobox with no first appearance links"""
    assert CharInfoBoxParser(["first appearance="]).parse().get("first_href") is None


"""
Status
"""


def test_infobox_status_linebreaks():
    """Parses infobox with multiple status split by linebreaks <br>"""
    assert (
        CharInfoBoxParser(["status={{Status|Deceased<br />(''Soul Consumed'')}}"])
        .parse()
        .get("status")
        == "Deceased (''Soul Consumed'')"
    )


def test_infobox_status_html_spoiler():
    """Parses infobox status with spoiler HTML"""
    assert (
        CharInfoBoxParser(
            [
                'status=<div class="mw-collapsible mw-collapsed" data-expandtext="Show Spoiler" data-collapsetext="Hide Spoiler">Alive</div>'
            ]
        )
        .parse()
        .get("status")
        == "Alive"
    )


def test_infobox_status_strips_whitespace():
    """Parses infobox status and strips out any leading or trailing whitespace"""
    assert (
        CharInfoBoxParser(
            [
                'status=<div class="mw-collapsible mw-collapsed" data-expandtext="Show Spoiler" data-collapsetext="Hide Spoiler">\nUnknown</div>'
            ]
        )
        .parse()
        .get("status")
        == "Unknown"
    )


def test_infobox_no_status():
    """Parses infobox without status"""
    assert CharInfoBoxParser([]).parse().get("status") is None
