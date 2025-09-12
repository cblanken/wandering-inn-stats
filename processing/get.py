"""Module to download every chapter from the links in the Wandering Inn Table of Contents"""

from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from itertools import chain
import hashlib
import random
import re
from sys import stderr
import time
from bs4 import BeautifulSoup, Tag
import requests
import requests.exceptions
from fake_useragent import UserAgent
from .exceptions import PatreonChapterError, ChapterPartitionsOverlappingError, TooManyAuthorsNotes
from typing import Any

BASE_URL: str = "https://www.wanderinginn.com"


def remove_bracketed_ref_number(s: str) -> str:
    """Remove a square bracketed reference number from a string"""
    splits = [x.split("]") for x in s.split("[")]

    # Filter out reference numbers
    if len(splits) > 1:
        return "".join(list(filter(lambda x: not x.isnumeric(), list(chain(*splits)))))
    return s


class Session:
    """Session object to download webpages via requests"""

    def __init__(
        self,
        max_tries: int = 10,
        throttle: float = 2.0,
    ) -> None:
        print("> Connecting to session...")
        self.__session = requests.session()
        self.__tries = 0  # resets after a sucessful chapter download
        self.__max_tries = max_tries
        self.__throttle = throttle
        self.__last_get = 0

    def get(self, url: str, timeout: int = 10, ignore_throttle: bool = False) -> requests.Response | None:
        """Perform a GET request to [url]"""
        resp = None
        # Add jitter to throttle time
        throttle = random.uniform(0.75, 1.25) * self.__throttle
        if not ignore_throttle:
            while time.time() - self.__last_get < throttle:
                # Note: the timing precision for the throttle should only be to 0.1
                # Anything beyond that will be effectively ignored due to the sleep
                time.sleep(0.1)
        self.__last_get = time.time()
        while self.__tries < self.__max_tries:
            resp = self.__session.get(
                url=url,
                headers={"User-Agent": UserAgent().random},
                allow_redirects=True,
                timeout=timeout,
            )

            if resp.status_code >= 400 and resp.status_code <= 499:
                self.__tries += 1
            else:
                self.__tries = 0
                return resp

        print("Cannot re-attempt download. Too many retries. Must reset to continue.")
        return None

    def reset_tries(self) -> None:
        self.__tries = 0


def extract_chapter_content(soup: BeautifulSoup) -> Tag:
    content = soup.select_one(".entry-content")
    if content is None:
        msg = "The Chapter soup contains no .entry-content"
        raise ValueError(msg)

    return content


def match_links(line: str) -> bool:
    link_re = re.compile(r".*http[s]?:\/\/.*")
    return bool(link_re.match(line))


def match_pre_note_line_start(line: str) -> bool:
    """Identifies a line with a prenote marking at the start of the line or a link"""
    parens_pre_note_start_re = re.compile(r"^\(.*")
    square_bracket_pre_note_start_re = re.compile(r"^\[.*")
    angle_bracket_pre_note_start_re = re.compile(r"^\<.*")

    return any(
        (
            pattern.match(line)
            for pattern in [
                parens_pre_note_start_re,
                square_bracket_pre_note_start_re,
                angle_bracket_pre_note_start_re,
            ]
        )
    )


def match_pre_note_line_end(line: str) -> bool:
    """Identifies a line with a prenote marking at the end of the line"""
    parens_pre_note_end_re = re.compile(r".*\)$")
    square_bracket_pre_note_end_re = re.compile(r".*\]\n?$")
    angle_bracket_pre_note_end_re = re.compile(r".*\>\n?$")

    return any(
        (
            pattern.match(line)
            for pattern in [
                parens_pre_note_end_re,
                square_bracket_pre_note_end_re,
                angle_bracket_pre_note_end_re,
            ]
        )
    )


def identify_pre_note_range(content_lines: list[str]) -> range:
    # Capture any pre-notes (these exclude explicitly marked  Author's notes)
    signed_pre_note_re = re.compile(r".*[-—][ ]?[Pp]irateaba.*")
    pre_note_range: range = range(0)
    for chapter_index, chapter_line in enumerate(content_lines[:3]):
        if match_pre_note_line_start(chapter_line):
            empty_line_cnt = 0
            for chapter_index_2, chapter_line_2 in enumerate(content_lines[chapter_index:20]):
                if empty_line_cnt > 3:
                    pre_note_range = range(chapter_index + chapter_index_2)
                    break
                if chapter_line_2.strip() == "":
                    empty_line_cnt += 1
                if match_pre_note_line_end(chapter_line_2):
                    pre_note_range = range(chapter_index + chapter_index_2 + 1)
                    break

    # Capture up to any links
    for chapter_index, chapter_line in enumerate(content_lines[:20]):
        if match_links(chapter_line) and chapter_index > pre_note_range.stop:
            pre_note_range = range(chapter_index + 1)

    # Capture up to a signature in the pre-note
    for chapter_index, chapter_line in enumerate(content_lines[:20]):
        if (
            any(signed_pre_note_re.match(split_line) for split_line in chapter_line.split("\n"))
            and chapter_index > pre_note_range.stop
        ):
            pre_note_range = range(chapter_index + 1)

    return pre_note_range


def parse_chapter_content(soup: BeautifulSoup) -> dict:
    content = extract_chapter_content(soup)

    if content is None:
        msg = "Chapter content cannot be parsed from None"
        raise ValueError(msg)

    chapter_data = {}
    content_children = list(content.children)

    # Exclude last two lines which include the previous and next chapter links
    content_lines: list[str] = [element.get_text() for element in content_children[:-2]]

    # Ignore Patreon locked chapters
    if len(content_lines) < 10 and any(("Patreon" in line for line in content_lines[:9])):
        raise PatreonChapterError

    # Exclude fanart images, links, and credits at end of chapter from parsing
    fanart_credit_pattern = re.compile(r".*([Bb]luesky|[Dd]eviant[Aa]rt|[Ii]nstagram|[Kk]o-?[Ff]i|[Tt]witter).*")
    first_img_index = len(content_lines)
    for i, child in enumerate(reversed(content_children)):
        if type(child) is Tag and (child.select("img") or fanart_credit_pattern.match(child.text)):
            first_img_index = len(content_children) - i
            content_lines = content_lines[
                : first_img_index - 3
            ]  # include additional lines to catch any credit text before the first img or a tag
        # Only check the last 200 lines of the chapter
        if i > 200:
            break

    pre_note_range = identify_pre_note_range(content_lines)
    pre_note_lines = content_lines[: pre_note_range.stop]

    # Capture note marked "Author's Note"
    authors_note_re = re.compile(r"(Actual )?Author['|’]?s['|’]? [N|n]ote.*")
    authors_note_count = 0
    authors_note_ranges: list[range] = []
    for chapter_index, chapter_line in enumerate(content_lines):
        if authors_note_re.match(chapter_line.strip()):
            authors_note_ranges.append(range(chapter_index, len(content_lines)))
            empty_line_cnt = 0
            for i, author_note_line in enumerate(content_lines[chapter_index:], start=chapter_index):
                if len(author_note_line.strip()) == 0:
                    empty_line_cnt += 1
                    if empty_line_cnt >= 4:
                        authors_note_ranges[authors_note_count] = range(
                            authors_note_ranges[authors_note_count].start, i
                        )
                        break
                else:
                    empty_line_cnt = 0

            authors_note_count += 1

    authors_note_lines = chain(
        "\n".join(line.strip() for line in content_lines[r.start : r.stop] if line.strip() != "")
        for r in authors_note_ranges
    )

    def ranges_overlap(r1: range, r2: range) -> bool:
        return r1.start > r2.start and r2.stop > r1.start or r1.start < r2.start and r1.stop > r2.start

    # Check for pre-note overlapping any authors notes
    if any(pre_note_range.stop > r.start for r in authors_note_ranges):
        msg = "The pre-note overlaps (one of) the Authors' notes"
        raise ChapterPartitionsOverlappingError(msg)

    # Check for any author's notes overlapping each other
    if any(ranges_overlap(r1, r2) for r1 in authors_note_ranges for r2 in authors_note_ranges):
        msg = "Author's note ranges are overlapping"
        raise ChapterPartitionsOverlappingError(msg)

    # Build chapter text based on line ranges for pre-note and author's note(s)
    match authors_note_count:
        case 0:
            chapter_lines = [line.strip() for line in content_lines[pre_note_range.stop :] if line.strip() != ""]
        case 1:
            chapter_lines = [
                line.strip()
                for line in chain(
                    content_lines[pre_note_range.stop : authors_note_ranges[0].start - 1],
                    content_lines[authors_note_ranges[0].stop :],
                )
                if line.strip() != ""
            ]
        case 2:
            # Ensure chapter content between multiple authors notes is captured
            chapter_lines = [
                line.strip()
                for line in chain(
                    content_lines[pre_note_range.stop : authors_note_ranges[0].start],
                    content_lines[authors_note_ranges[0].stop + 1 : authors_note_ranges[1].start],
                )
                if line.strip() != ""
            ]
        case _:
            raise TooManyAuthorsNotes

    chapter_data["text"] = "\n".join([line.strip() for line in chapter_lines]).strip() + "\n"
    chapter_data["authors_note"] = "\n".join(authors_note_lines) + "\n"
    chapter_data["pre_note"] = "\n".join([line.strip() for line in pre_note_lines if line.strip() != ""]).strip() + "\n"

    try:
        word_count = len(chapter_data["text"].split())

        authors_note_word_count = len(chapter_data["authors_note"].split())
        digest: str = hashlib.sha256(chapter_data["text"].encode("utf-8")).hexdigest()
        chapter_data["metadata"] = {
            "word_count": word_count,
            "authors_note_word_count": authors_note_word_count,
            "digest": digest,
        }

    except IndexError:
        # TODO: log missing data (title, pub_time, or mod_time)
        pass

    return chapter_data


def parse_chapter_response(response: requests.Response) -> dict:
    """Parse data from chapter Response"""
    chapter_data = {}

    # Parse chapter metadata from Response object
    soup: BeautifulSoup = BeautifulSoup(response.content, "html.parser")

    try:
        chapter_data = parse_chapter_content(soup)
    except ValueError:
        raise

    try:
        title = soup.select(".entry-title")[0].get_text()
        pub_time = soup.select("meta[property='article:published_time']")[0].get("content")
        mod_time = soup.select("meta[property='article:modified_time']")[0].get("content")
        dl_time: str = str(datetime.now().astimezone())

        chapter_data["html"] = str(soup.select_one(".entry-content"))
        chapter_data["metadata"] |= {
            "title": title,
            "pub_time": pub_time,
            "mod_time": mod_time,
            "dl_time": dl_time,
            "url": response.url,
        }
    except IndexError as exc:
        print(f"Missing metadata at {response.url}. Exception: {exc}")

    return chapter_data


def save_file(filepath: Path, text: str, clobber: bool = False) -> bool:
    """Write chapter text content to file"""
    if filepath.exists() and not clobber:
        return False

    with filepath.open("w", encoding="utf-8") as file:
        file.write(text)
        return True


class TableOfContents:
    """Table of Contents scraper to query for any needed info"""

    def __init__(self, session: Session | None = None) -> None:
        self.domain: str = "www.wanderinginn.com"
        self.url: str = f"https://{self.domain}/table-of-contents"
        if session:
            if not isinstance(session, Session):
                msg = "The session argument must be an appropriate Session type to retrieve the table of contents"
                raise TypeError(
                    msg,
                )
            self.response = session.get(self.url)
        else:
            self.response = requests.get(self.url, timeout=10)
            print("Request for Table of Contents timed out!", file=stderr)

        self.volume_data: OrderedDict[str, OrderedDict[str, str]]

        if self.response is None:
            self.soup = self.chapter_links = None
            self.volume_data = OrderedDict()
            print(
                "Table of Contents could not be reached! ToC `volume_data` will be `None`",
                file=stderr,
            )
            return

        # TODO: add check to not download chapter with password prompt
        self.soup = BeautifulSoup(self.response.content, "html.parser")
        self.chapter_links = self.__get_chapter_links()
        self.volume_data = self.__get_volume_data()

    def __get_chapter_links(self) -> list[str]:
        """Scrape table of contents for a list of chapter links"""
        if self.soup is None:
            return []

        return [f"https://{self.domain}" + link.get("href") for link in self.soup.select(".chapter-entry a")]

    def __get_volume_data(self) -> OrderedDict[str, OrderedDict[str, str]]:
        """Return dictionary containing tuples (volume_title, chapter_indexes)
        by volume ID"""

        def get_title_and_href_from_a_tag(element: Tag) -> tuple[Any, ...]:
            """Return tuple of text and href from <a> tag

            Args:
                element: an <a> Tag element
            """
            # chapter_a = element.find_next("a")
            chapter_name = element.text
            chapter_href = element.get("href")
            return (chapter_name, chapter_href)

        volumes: OrderedDict[str, OrderedDict[str, str]] = OrderedDict()
        if self.soup is None:
            return volumes

        vol_elements = self.soup.select(".volume-wrapper")

        volumes = OrderedDict()
        for vol_ele in vol_elements:
            vol_name = vol_ele.select_one(".volume-header").text.strip()
            volumes[vol_name] = OrderedDict()

            # Search for books
            book_sections = vol_ele.select(".book-wrapper")
            for section in book_sections:
                # Check for book heading
                heading_div = section.select_one(".book-header .head-book-title")

                # Use book title or default to "Unreleased" for sections without a released audiobook
                book_name = heading_div.text if heading_div else "Unreleased"

                volumes[vol_name][book_name] = OrderedDict()

                chapters = section.select(".book-body a")

                # Populate chapters for each book by title
                for chapter in chapters:
                    chapter_name, chapter_href = get_title_and_href_from_a_tag(chapter)
                    volumes[vol_name][book_name][chapter_name] = chapter_href

        return volumes

    def get_book_titles(self, is_released: bool = False) -> list[Any]:
        """Get a list of Book titles from TableOfContents"""
        if is_released:
            return [x.text.strip() for x in self.soup.select(".book:not(.unreleased)")]
        return [x.text.strip() for x in self.soup.select(".book")]
