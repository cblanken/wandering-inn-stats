import pytest
from processing.get import parse_chapter_content
from bs4 import BeautifulSoup, Tag
from pathlib import Path


@pytest.fixture()
def ch1_html_content() -> BeautifulSoup:
    """Sample chapter #1"""
    with open(Path(__file__).parent / "samples/8.00/8.00.html", encoding="utf-8") as fp:
        soup = BeautifulSoup(fp)
        soup.get("html")
        return soup


@pytest.fixture()
def ch1_text_content() -> str:
    """Sample Author's Note #1"""
    with open(Path(__file__).parent / "samples/8.00/8.00.txt", encoding="utf-8") as fp:
        return fp.read()


@pytest.fixture
def ch1_authors_note() -> str:
    """Sample Author's Note #1"""
    with open(
        Path(__file__).parent / "samples/8.00/8.00_authors_note.txt", encoding="utf-8"
    ) as fp:
        return fp.read()


@pytest.fixture
def ch1_parens_note() -> str:
    """Sample parenthesized note #1"""
    with open(
        Path(__file__).parent / "samples/8.00/8.00_pre_note.txt", encoding="utf-8"
    ) as fp:
        return fp.read()


def test_text_content(ch1_html_content, ch1_text_content):
    """Most author's notes appear at the end of the chapter with the typical 'Author's Note' indicator"""
    ch1_data = parse_chapter_content(ch1_html_content)
    assert ch1_data.get("text") == ch1_text_content


def test_author_note_at_start():
    """Some author's notes appear at the start of the chapter with the typical 'Author's Note' indicator"""
    pass


def test_author_note_at_end(ch1_html_content, ch1_authors_note):
    """Most author's notes appear at the end of the chapter with the typical 'Author's Note' indicator"""
    ch1_data = parse_chapter_content(ch1_html_content)
    assert ch1_data.get("authors_note") == ch1_authors_note


def test_parenthesized_author_note_at_start(ch1_html_content, ch1_parens_note):
    """Sometimes pirateaba provides a short aside in parentheses in the first couple lines"""
    ch1_data = parse_chapter_content(ch1_html_content)
    assert ch1_data.get("pre_parens_note") == ch1_parens_note


def test_ignore_fanart_attributions():
    """Many chapters include fanart appended to the end of the chapter which should not be inluded in the chapter text"""
    pass
