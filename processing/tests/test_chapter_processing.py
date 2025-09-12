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
        at the start of the chapter."""
        data = parse_chapter_content(html_content)

        pre_note = data.get("pre_note")
        assert pre_note is not None
        assert (
            pre_note
            == "(A fellow author and friend of mine, Quill, is releasing a new story! Blood Eagle: Norse Progression Fantasy is out now on Royalroad! Consider giving it a read:\nhttps://www.royalroad.com/fiction/91540/blood-eagle-norse-progression-fantasy)\n"
        )

        parsed_authors_note = data.get("authors_note")
        assert parsed_authors_note is not None
        assert parsed_authors_note == authors_note

        chapter_text = data.get("text")
        assert chapter_text is not None
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


class TestChapterProcessing_10_00_L:
    @pytest.fixture
    def html_content(scope="class") -> BeautifulSoup:
        with Path.open(Path(__file__).parent / "samples/10.00_L/chapter.html", encoding="utf-8") as fp:
            soup = BeautifulSoup(fp)
            soup.get("html")
            return soup

    def test_multiple_authors_notes(self, html_content):
        content = parse_chapter_content(html_content)
        authors_note_text = content.get("authors_note")
        assert authors_note_text is not None
        assert "No, but for real, I would" in authors_note_text
        assert "Trolling readers is an art" in authors_note_text
        assert "Look forward to that box on Tuesday" in authors_note_text

        assert (
            authors_note_text
            == """Author’s Notes:
No, but for real, I wouldn’t do that to you. Also, for clarity, Lyonette’s level-ups are from after the Solstice. Continue onwards!
—pirateaba
Actual Author’s Note:
Trolling readers is an art. At some point in my life, I wondered if I’d be white-haired and distinguished, one of those authors who has a reputation. Then I thought about other authors who get that old, and they have fun with things.
No one gets old in a set way. Age is something that can affect someone very young, and I have heard people in their nineties say they feel like they’re still in their twenties.
So, the point I’m making is that I hope I enjoy annoying readers no matter how old I get.
Hello, and welcome to Volume 10. I’m trying to make it smile more. My month off? It was good. I wrote two blog posts on it, but in truth, it wasn’t an entire month, and what I said last year holds. I figured out how to vacation near the end, I wanted more, and I did fear my return because I didn’t know if I ‘remembered’ how to write.
Perhaps that’s also because, after a volume ending, I have to reset. The battles are done, but the effects aren’t over…and then you’re a bit lost, right? I don’t want to imagine what it’s actually like for any kind of event or conflict for people in real life.
Ah, well, I’m rambling a bit, but maybe that’s how we’ll start. With an attempt at both easing into things and trying to find whatever normal used to be. And as ever, I hope you enjoy it. I mean it; that’s been the point the whole time.
This month will be interesting. I just learned I have a hard deadline to do some revisions to Book 12: The Witch of Webs by the end of the month or I, uh, delay all audiobook releases for this year. So I’d better work hard on that! But I’ll be putting regular chapters out…I think it’ll work.
I have energy at the start of the year and, once I do that, I’ll have 0 other writing projects besides The Wandering Inn for once. Which will be the first time for like 2-3 years that’s happened! Not that it’s a bad thing, but what a thing, huh? I’m also planning a vacation to a country in April, but I’ll probably try to work during that. This is all the news from me.
Look forward to that box on Tuesday, and thanks for reading!
—pirateaba
PS. I’ll be featuring lots of art but the backlog is amazing–and huge! Have you seen some of this art like the comics, the fake Gazi book, and everything else? Even a tattoo!
"""
        )


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


class TestChapterProcessing_10_18_E:
    @pytest.fixture
    def html_content(scope="class") -> BeautifulSoup:
        with Path.open(Path(__file__).parent / "samples/10.18_E/chapter.html", encoding="utf-8") as fp:
            soup = BeautifulSoup(fp)
            soup.get("html")
            return soup

    def test_ignore_links_at_start(self, html_content):
        """This chapter has some links deeper in the pre note"""
        content = parse_chapter_content(html_content)
        text_content = content.get("text")
        assert text_content is not None
        assert "www.amazon.com" not in text_content
        assert "www.audible.com" not in text_content


class TestChapterProcessing_10_10_E_PT1:
    @pytest.fixture
    def html_content(scope="class") -> BeautifulSoup:
        with Path.open(Path(__file__).parent / "samples/10.10_E_PT1/chapter.html", encoding="utf-8") as fp:
            soup = BeautifulSoup(fp)
            soup.get("html")
            return soup

    def test_multiline_bracketed_pre_note(self, html_content):
        content = parse_chapter_content(html_content)
        pre_note = content.get("pre_note")
        assert pre_note is not None
        assert "[To celebrate the upcoming audiobook release of Gravesong" in pre_note  # start of pre-note
        assert "Undead, ghosts, and more are to" in pre_note
        assert "To inspire our artists, Haunting Hues" in pre_note
        assert "And don’t forget to keep an eye on Cognita…]" in pre_note  # end of pre-note

        text = content.get("text")
        assert text is not None
        assert "[To celebrate the upcoming audiobook release of Gravesong" not in text
        assert "Undead, ghosts, and more are to" not in text
        assert "To inspire our artists, Haunting Hues" not in text
        assert "And don’t forget to keep an eye on Cognita…]" not in text


class TestChapterProcessing_Interlude_Saliss_The_Architect:
    @pytest.fixture
    def html_content(scope="class") -> BeautifulSoup:
        with Path.open(
            Path(__file__).parent / "samples/interlude_saliss_the_architect/chapter.html", encoding="utf-8"
        ) as fp:
            soup = BeautifulSoup(fp)
            soup.get("html")
            return soup

    def test_authors_note_mentioning_authors_note(self, html_content):
        content = parse_chapter_content(html_content)
        authors_note = content.get("authors_note")
        assert (
            authors_note
            == """Author’s Note:\nThis is a reminder of two things to you. One—why I had to announce I’m moving down to 30,000 words.\nDoing two chapters doesn’t work. I thought to myself, ‘pirateaba’, because I think in the third person, ‘pirateaba, you’ve got to do a short chapter because\xa0 you’re too tired to do the third Erin chapter justice’.\nSo I planned out a 10,000, maybe 15,000 word chapter about Saliss on Saturday, after posting the last one. Did a pretty decent outline, then started the next day to write it in one go. Edited Wednesday.\n24,000 words.\nSigh.\nWriting this many words does drain my energy battery considerably. Hopefully with a day off, I’ll rally enough come Thursday to do the Erin chapter justice but this is why. This is why.\nAnyways, the other lesson is that you can’t just sit on your thumbs and wait to well, write a chapter like this. There’s a good quote about hesitation. About waiting for the ‘right moment’ and compromising until then.\nI choose to apply it to arcs that aren’t easy, or fun for me to write. They have to happen, and I cannot wait until I am in the right mood or have all my ducks in a row because they never will be. It is imperfect; I was editing the last…five hours which is why this chapter is out later than usual. But even if imperfect, we forge ahead.\nOr sometimes, we take a break! Next month. I do think I’m willing to push harder this month because of my vacation and the reduced workload next month. Did I mention going on a vacation to a country? Do I tell people what country? Eh, you’ll never find me in Puerto Rico. I hear it’s nice.\nWait, am I going to that country or another one? I’d better check my tickets. (A few were being floated around, okay? I have tickets. I just don’t actually know which one it is.)\nThat’s all from me! I’m tired. I wonder if anyone reads The Wandering Inn, in Puerto Rico. I wonder what’s for dinner. I wonder how I’m going to finish this Author’s Note.\n"""
        )


# TODO: chapter may have marked Author's Note at start and end of chapter

# TODO: confirm digest/hash consistency

# TODO: catch password message in pre-note (Chapter 10.45)

# TODO: catch author's notes that appear at the start of the chapter with the typical 'Author's Note' indicator"""

# TODO: chapter 9.01 has a complex author's note with a short aside at the end delimited by dashes before then speaking in the framing of the author's note again, THEN listing chapter fanart

# TODO: chapter 10.10 E (Pt. 1) has a <div> in the fanart credits that prevents the fanart credit exclusion parsing from catching all of them

# TODO: chapter 10.17 has a <button> at the start an mentions enabling mic permission, this should parse into the pre-note
