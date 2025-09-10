import pytest
from processing.get import parse_chapter_content
from bs4 import BeautifulSoup
from pathlib import Path
from processing.exceptions import PatreonChapterError


class TestChapterProcessing_Simple:
    """
    Test simple chapter with no author's note (intro or outro) or fanart attributions
    These tests should be used as a helpful baseline.
    """

    @pytest.fixture
    def html_content(scope="class") -> BeautifulSoup:
        with Path.open(Path(__file__).parent / "samples/2.01/chapter.html", encoding="utf-8") as fp:
            soup = BeautifulSoup(fp)
            soup.get("html")
            return soup

    @pytest.fixture
    def text_content(scope="class") -> str:
        with Path.open(Path(__file__).parent / "samples/2.01/chapter.txt", encoding="utf-8") as fp:
            return fp.read()

    def test_simple_chapter_content(self, html_content, text_content):
        content = parse_chapter_content(html_content)
        text = content.get("text")
        assert content is not None
        assert text == text_content


class TestChapterProcessing_8_00:
    @pytest.fixture
    def html_content(scope="class") -> BeautifulSoup:
        with Path.open(Path(__file__).parent / "samples/8.00/chapter.html", encoding="utf-8") as fp:
            soup = BeautifulSoup(fp)
            soup.get("html")
            return soup

    @pytest.fixture
    def text_content(scope="class") -> str:
        with Path.open(Path(__file__).parent / "samples/8.00/chapter.txt", encoding="utf-8") as fp:
            return fp.read()

    @pytest.fixture
    def authors_note(scope="class") -> str:
        with Path.open(Path(__file__).parent / "samples/8.00/authors_note.txt", encoding="utf-8") as fp:
            return fp.read()

    @pytest.fixture
    def pre_note(scope="class") -> str:
        with Path.open(Path(__file__).parent / "samples/8.00/pre_note.txt", encoding="utf-8") as fp:
            return fp.read()

    def test_text_content(self, html_content: BeautifulSoup, text_content: str):
        """Most author's notes appear at the end of the chapter with the typical 'Author's Note' indicator"""
        data = parse_chapter_content(html_content)
        assert data.get("text") == text_content

    def test_author_note_at_start(self, pre_note: str):
        """Some author's notes appear at the start of the chapter with the typical 'Author's Note' indicator"""
        # TODO

    def test_author_note_at_end(self, html_content: BeautifulSoup, authors_note: str):
        """Most author's notes appear at the end of the chapter with the typical 'Author's Note' indicator"""
        data = parse_chapter_content(html_content)
        assert data.get("authors_note") == authors_note

    def test_parenthesized_author_note_at_start(self, html_content: BeautifulSoup, pre_note: str):
        """Sometimes pirateaba provides a short aside in parentheses in the first couple lines"""
        data = parse_chapter_content(html_content)
        assert data.get("pre_note") == pre_note


class TestChapterProcessing_TheRoots3:
    @pytest.fixture
    def html_content(scope="class") -> BeautifulSoup:
        with Path.open(Path(__file__).parent / "samples/TheRoots3/chapter.html", encoding="utf-8") as fp:
            soup = BeautifulSoup(fp)
            soup.get("html")
            return soup

    @pytest.fixture
    def text_content(scope="class") -> str:
        with Path.open(Path(__file__).parent / "samples/TheRoots3/chapter.txt", encoding="utf-8") as fp:
            return fp.read()

    @pytest.fixture
    def authors_note(scope="class") -> str:
        with Path.open(Path(__file__).parent / "samples/TheRoots3/authors_note.txt", encoding="utf-8") as fp:
            return fp.read()

    @pytest.fixture
    def pre_note(scope="class") -> str:
        with Path.open(Path(__file__).parent / "samples/TheRoots3/pre_note.txt", encoding="utf-8") as fp:
            return fp.read()

    def test_text_does_not_contain_authors_note(self, html_content: BeautifulSoup):
        """The chapter text should not contain any text from author's note"""
        data = parse_chapter_content(html_content)
        authors_note = data.get("authors_note")
        if authors_note is None:
            msg = "Empty author's note"
            raise ValueError(msg)
        for line in authors_note.split("\n"):
            if not line.isspace and line != "":
                assert line not in data.get("text")

    def test_signed_pre_note_detected(self, html_content: BeautifulSoup):
        """Signed pre-notes by the author should not be detected by parser"""
        data = parse_chapter_content(html_content)
        pre_note = data.get("pre_note")

        if pre_note is None:
            msg = "Empty author's note"
            raise ValueError(msg)

        assert (
            pre_note
            == "Did you click ‘Slam’ on last chapter and find the other two parts? If you didn’t, go and do that.\n—pirateaba\n"
        )

    def test_signed_pre_note_not_in_chapter_text(self, html_content: BeautifulSoup):
        """Signed pre-notes by the author should not be included in the chapter text"""
        data = parse_chapter_content(html_content)
        pre_note = data.get("pre_note")

        if pre_note is None:
            msg = "Empty author's note"
            raise ValueError(msg)
        for line in pre_note.split("\n"):
            if not line.isspace and line != "":
                assert line not in data.get("text")


class TestChapterProcessing_10_22_R:
    @pytest.fixture
    def html_content(scope="class") -> BeautifulSoup:
        with Path.open(Path(__file__).parent / "samples/10.22_R/chapter.html", encoding="utf-8") as fp:
            soup = BeautifulSoup(fp)
            soup.get("html")
            return soup

    @pytest.fixture
    def text_content(scope="class") -> str:
        with Path.open(Path(__file__).parent / "samples/10.22_R/chapter.txt", encoding="utf-8") as fp:
            return fp.read()

    @pytest.fixture
    def authors_note(scope="class") -> str:
        with Path.open(Path(__file__).parent / "samples/10.22_R/authors_note.txt", encoding="utf-8") as fp:
            return fp.read()

    def test_parens_pre_note_and_pre_authors_note(
        self, html_content: BeautifulSoup, authors_note: str, text_content: str
    ):
        """A chapter may have a parenthesized pre-note in addition to an Author's note
        at the start of the chapter"""
        data = parse_chapter_content(html_content)

        pre_note = data.get("pre_note")
        if pre_note is None:
            msg = "Empty pre note"
            raise ValueError(msg)

        assert (
            pre_note
            == "(A fellow author and friend of mine, Quill, is releasing a new story! Blood Eagle: Norse Progression Fantasy is out now on Royalroad! Consider giving it a read:\n\n\nhttps://www.royalroad.com/fiction/91540/blood-eagle-norse-progression-fantasy)\n"
        )

        authors_note = data.get("authors_note")
        if authors_note is None:
            msg = "Empty pre note"
            raise ValueError(msg)

        assert authors_note == authors_note

        chapter_text = data.get("text")
        if chapter_text is None:
            raise ValueError

        assert chapter_text == text_content

    def test_ignore_fanart_attributions(self, html_content: BeautifulSoup):
        """Many chapters include fanart appended to the end of the chapter which should not be included in the chapter text"""
        content = parse_chapter_content(html_content)
        text = content.get("text")
        assert text is not None

        pre_note = content.get("pre_note")
        assert pre_note is not None

        authors_note = content.get("authors_note")
        assert authors_note is not None

        flags = ["Jewel, by Kalabaza, Kuheno, and Pon", "Ko-Fi:", "Instagram:", "Twitter:"]
        for f in flags:
            assert f not in text
            assert f not in pre_note
            assert f not in authors_note


class TestChapterProcessing_10_01_L:
    @pytest.fixture
    def html_content(scope="class") -> BeautifulSoup:
        with Path.open(Path(__file__).parent / "samples/10.01_L/chapter.html", encoding="utf-8") as fp:
            soup = BeautifulSoup(fp)
            soup.get("html")
            return soup

    @pytest.fixture
    def text_content(scope="class") -> str:
        with Path.open(Path(__file__).parent / "samples/10.01_L/chapter.txt", encoding="utf-8") as fp:
            return fp.read()

    @pytest.fixture
    def pre_note(scope="class") -> str:
        with Path.open(Path(__file__).parent / "samples/10.01_L/pre_note.txt", encoding="utf-8") as fp:
            return fp.read()

    def test_bracket_pre_note(self, html_content, pre_note):
        content = parse_chapter_content(html_content)

        assert pre_note == content.get("pre_note")
        text_content = content.get("text")
        assert text_content is not None
        assert "Will Wight is Kickstarting an animation" not in text_content


class TestChapterProcessing_10_07:
    @pytest.fixture
    def html_content(scope="class") -> BeautifulSoup:
        with Path.open(Path(__file__).parent / "samples/10.07/chapter.html", encoding="utf-8") as fp:
            soup = BeautifulSoup(fp)
            soup.get("html")
            return soup

    @pytest.fixture
    def authors_note(scope="class") -> str:
        with Path.open(Path(__file__).parent / "samples/10.07/authors_note.txt", encoding="utf-8") as fp:
            return fp.read()

    def test_ignore_links_at_start(self, html_content):
        content = parse_chapter_content(html_content)
        text_content = content.get("text")
        assert text_content is not None
        assert "www.amazon.com" not in text_content
        assert "www.audible.com" not in text_content

    def test_authors_note_captured_correctly(self, authors_note, html_content):
        content = parse_chapter_content(html_content)
        authors_note_text = content.get("authors_note")
        assert authors_note_text is not None
        assert str(authors_note_text) == str(authors_note)


class TestChapterProcessing_Patreon:
    @pytest.fixture
    def html_content(scope="class") -> BeautifulSoup:
        with Path.open(Path(__file__).parent / "samples/patreon_locked_chapter/chapter.html", encoding="utf-8") as fp:
            soup = BeautifulSoup(fp)
            soup.get("html")
            return soup

    def test_patreon_locked_chapter_raise_error(self, html_content):
        with pytest.raises(PatreonChapterError):
            parse_chapter_content(html_content)


# TODO: chapter may have marked Author's Note at start and end of chapter

# TODO: confirm digest/hash consistency
