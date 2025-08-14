import pytest
from processing.get import parse_chapter_content
from bs4 import BeautifulSoup
from pathlib import Path


@pytest.fixture
def ch1_html_content() -> BeautifulSoup:
    """Sample chapter #1"""
    with Path.open(Path(__file__).parent / "samples/8.00/8.00.html", encoding="utf-8") as fp:
        soup = BeautifulSoup(fp)
        soup.get("html")
        return soup


@pytest.fixture
def ch1_text_content() -> str:
    """Sample Author's Note #1"""
    with Path.open(Path(__file__).parent / "samples/8.00/8.00.txt", encoding="utf-8") as fp:
        return fp.read()


@pytest.fixture
def ch1_authors_note() -> str:
    """Sample Author's Note #1"""
    with Path.open(Path(__file__).parent / "samples/8.00/8.00_authors_note.txt", encoding="utf-8") as fp:
        return fp.read()


@pytest.fixture
def ch1_pre_note() -> str:
    """Sample parenthesized note #1"""
    with Path.open(Path(__file__).parent / "samples/8.00/8.00_pre_note.txt", encoding="utf-8") as fp:
        return fp.read()


@pytest.fixture
def ch2_html_content() -> BeautifulSoup:
    """Sample chapter #2"""
    with Path.open(Path(__file__).parent / "samples/TheRoots3/chapter.html", encoding="utf-8") as fp:
        soup = BeautifulSoup(fp)
        soup.get("html")
        return soup


@pytest.fixture
def ch2_text_content() -> str:
    """Sample Author's Note #2"""
    with Path.open(Path(__file__).parent / "samples/TheRoots3/chapter.txt", encoding="utf-8") as fp:
        return fp.read()


@pytest.fixture
def ch2_authors_note() -> str:
    """Sample Author's Note #2"""
    with Path.open(Path(__file__).parent / "samples/TheRoots3/authors_note.txt", encoding="utf-8") as fp:
        return fp.read()


@pytest.fixture
def ch2_pre_note() -> str:
    """Sample pre note #2"""
    with Path.open(Path(__file__).parent / "samples/TheRoots3/pre_note.txt", encoding="utf-8") as fp:
        return fp.read()


@pytest.fixture
def ch3_html_content() -> BeautifulSoup:
    """Sample chapter #3"""
    with Path.open(Path(__file__).parent / "samples/10.22_R/chapter.html", encoding="utf-8") as fp:
        soup = BeautifulSoup(fp)
        soup.get("html")
        return soup


@pytest.fixture
def ch3_text_content() -> str:
    """Sample chapter #3"""
    with Path.open(Path(__file__).parent / "samples/10.22_R/chapter.txt", encoding="utf-8") as fp:
        return fp.read()


@pytest.fixture
def ch3_authors_note() -> str:
    """Sample chapter #3"""
    with Path.open(Path(__file__).parent / "samples/10.22_R/authors_note.txt", encoding="utf-8") as fp:
        return fp.read()


# ------------------------------------------------------------------------
# ch1 tests
# ------------------------------------------------------------------------
def test_text_content(ch1_html_content, ch1_text_content):
    """Most author's notes appear at the end of the chapter with the typical 'Author's Note' indicator"""
    data = parse_chapter_content(ch1_html_content)
    assert data.get("text") == ch1_text_content


def test_author_note_at_start():
    """Some author's notes appear at the start of the chapter with the typical 'Author's Note' indicator"""


def test_author_note_at_end(ch1_html_content, ch1_authors_note):
    """Most author's notes appear at the end of the chapter with the typical 'Author's Note' indicator"""
    data = parse_chapter_content(ch1_html_content)
    assert data.get("authors_note") == ch1_authors_note


def test_parenthesized_author_note_at_start(ch1_html_content, ch1_pre_note):
    """Sometimes pirateaba provides a short aside in parentheses in the first couple lines"""
    data = parse_chapter_content(ch1_html_content)
    assert data.get("pre_note") == ch1_pre_note


def test_ignore_fanart_attributions():
    """Many chapters include fanart appended to the end of the chapter which should not be inluded in the chapter text"""


# ------------------------------------------------------------------------
# ch2 tests
# ------------------------------------------------------------------------
def test_text_does_not_contain_authors_note(ch2_html_content):
    """The chapter text should not contain any text from author's note"""
    data = parse_chapter_content(ch2_html_content)
    authors_note = data.get("authors_note")
    if authors_note is None:
        raise ValueError("Empty author's note")
    for line in authors_note.split("\n"):
        if not line.isspace and not line == "":
            assert line not in data.get("text")


def test_signed_pre_note_detected(ch2_html_content):
    """Signed pre-notes by the author should not be detected by parser"""
    data = parse_chapter_content(ch2_html_content)
    pre_note = data.get("pre_note")

    if pre_note is None:
        raise ValueError("Empty author's note")

    assert (
        pre_note
        == """Did you click ‘Slam’ on last chapter and find the other two parts? If you didn’t, go and do that.
—pirateaba
"""
    )


def test_signed_pre_note_not_in_chapter_text(ch2_html_content):
    """Signed pre-notes by the author should not be included in the chapter text"""
    data = parse_chapter_content(ch2_html_content)
    pre_note = data.get("pre_note")

    if pre_note is None:
        raise ValueError("Empty author's note")
    for line in pre_note.split("\n"):
        if not line.isspace and not line == "":
            assert line not in data.get("text")


# ------------------------------------------------------------------------
# ch3 tests
# ------------------------------------------------------------------------
def test_parens_pre_note_and_pre_authors_note(ch3_html_content, ch3_authors_note, ch3_text_content):
    """A chapter may have a parenthesized pre-note in addition to an Author's note
    at the start of the chapter"""
    data = parse_chapter_content(ch3_html_content)

    pre_note = data.get("pre_note")
    if pre_note is None:
        raise ValueError("Empty pre note")

    assert (
        pre_note
        == """(A fellow author and friend of mine, Quill, is releasing a new story! Blood Eagle: Norse Progression Fantasy is out now on Royalroad! Consider giving it a read:


https://www.royalroad.com/fiction/91540/blood-eagle-norse-progression-fantasy)
"""
    )

    authors_note = data.get("authors_note")
    if authors_note is None:
        raise ValueError("Empty pre note")

    assert authors_note == ch3_authors_note

    chapter_text = data.get("text")
    if chapter_text is None:
        raise ValueError

    assert chapter_text == ch3_text_content


# TODO: chapter may have marked Author's Note at start and end of chapter
