"""Module to download every chapter from the links in the Wandering Inn Table of Contents"""

import hashlib
import random
import re
import time
from collections import OrderedDict
from datetime import datetime
from enum import Enum
from itertools import chain
from pathlib import Path
from sys import stderr
from typing import Any, NamedTuple

import requests
import requests.exceptions
from bs4 import BeautifulSoup, Tag
from bs4.element import PageElement
from fake_useragent import UserAgent

from .exceptions import ChapterPartitionsOverlappingError, PatreonChapterError, TooManyAuthorsNotes

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


class REPair(NamedTuple):
    begin: re.Pattern  # symbol appears at beginning of line
    internal_end: re.Pattern  # the ending symbol of the pair appears before the end of the line
    end: re.Pattern  # symbol appears at end of line


PrenoteLineType = Enum("PrenoteLineType", ["SINGLE", "MULTI", "INCOMPLETE"])

pre_note_re_pairs: list[REPair] = [
    REPair(re.compile(r"^\(.*"), re.compile(r".*\(.*\)"), re.compile(r".*\)\n?$")),
    REPair(re.compile(r"^\[.*"), re.compile(r".*\[.*\]"), re.compile(r".*\]\n?$")),
    REPair(re.compile(r"^\<.*"), re.compile(r".*\<.*\>"), re.compile(r".*\>\n?$")),
    REPair(re.compile(r"^\{.*"), re.compile(r".*\{.*\}"), re.compile(r".*\}\n?$")),
    REPair(re.compile(r"^Pre-?[Cc]hapter Note"), re.compile(r".*"), re.compile(r":\s?$")),
]


def match_pre_note_line_start(line: str) -> REPair | None:
    """Identifies a line with a prenote marking at the start of the line or a link"""
    matching_pattern_pairs = [re_pair for re_pair in pre_note_re_pairs if re_pair.begin.match(line)]
    if len(matching_pattern_pairs) > 0:
        return matching_pattern_pairs[0]

    return None


def match_pre_note_line_end(line: str) -> REPair | None:
    """Identifies a line with a prenote marking at the end of the line"""
    matching_pattern_pairs = [re_pair for re_pair in pre_note_re_pairs if re_pair.end.match(line)]
    if len(matching_pattern_pairs) > 0:
        return matching_pattern_pairs[0]

    return None


def identify_pre_note_range(elements: list[PageElement]) -> range:
    """This function identifies the range of child elements of the main chapter .entry-content
    that correspond to the pre note of the chapter (these exclude explicitly marked  Author's notes)
    """
    square_bracket_exceptions = [re.compile(r".*Level \d+.?\].*"), re.compile(r".*\[Skill.*")]
    signed_pre_note_re = re.compile(r".*[-—][ ]?[Pp]irateaba.*")
    pre_note_range: range = range(0)

    for chapter_index, element in enumerate(elements[:8]):
        ele_text = element.get_text()
        if pre_note_begin := match_pre_note_line_start(ele_text):
            if any(p.match(ele_text) for p in square_bracket_exceptions):
                break

            if pre_note_begin.end.match(ele_text):
                # Opening pre-note with closing symbol i.e. single-line pre-note
                pre_note_range = range(chapter_index + 1)
            elif not pre_note_begin.internal_end.match(ele_text):
                # Opening pre-note without closing symbol i.e. multi-line pre-note
                empty_line_cnt = 0
                for multi_line_index, multi_line_ele in enumerate(elements[chapter_index:20]):
                    multi_line_ele_text = multi_line_ele.get_text()
                    if empty_line_cnt > 3:
                        pre_note_range = range(chapter_index + multi_line_index)
                        break
                    if multi_line_ele_text.strip() == "":
                        empty_line_cnt += 1
                    if match_pre_note_line_end(multi_line_ele_text):
                        pre_note_range = range(chapter_index + multi_line_index + 1)
                        break
            elif pre_note_begin.internal_end.match(ele_text):
                # Mostly likely matching a [RefType] or intro line
                pass

    # Capture up to any links
    for chapter_index, element in enumerate(elements[:40]):
        if match_links(element.get_text()) and chapter_index > pre_note_range.stop:
            pre_note_range = range(chapter_index + 1)

    # Capture up to a signature in the pre-note
    for chapter_index, element in enumerate(elements[:40]):
        if (
            any(signed_pre_note_re.match(split_line) for split_line in element.get_text().split("\n"))
            and chapter_index > pre_note_range.stop
        ):
            pre_note_range = range(chapter_index + 1)

    return pre_note_range


def identify_authors_note_ranges(elements: list[PageElement]) -> list[range]:
    """This function identifies the range of child elements of the main chapter .entry-content
    that correspond to the author's note(s) of the chapter
    """

    authors_note_re = re.compile(r"(^((((Actual )?Author['’]?s['’]?)|(Writ(ing|er.?s))) [N|n]ote.*)|(Song [Ll]ist:?))")
    signed_note_re = re.compile(r".*[-—][ ]?[Pp]irateaba.*")
    authors_ps_note_re = re.compile(r"P[Ss]\.?.*")
    authors_note_count = 0
    authors_note_ranges: list[range] = []
    for chapter_index, element in enumerate(elements):
        element_text = element.get_text()
        if authors_note_re.match(element_text.strip()):
            authors_note_ranges.append(range(chapter_index, len(elements)))
            empty_line_cnt = 0

            # Collect Author's note lines
            for i, author_note_ele in enumerate(elements[chapter_index + 1 :], start=chapter_index + 1):
                author_note_ele_text = author_note_ele.get_text()
                # Break out if another Author's note is found
                if authors_note_re.match(author_note_ele_text.strip()):
                    break

                authors_note_ranges[authors_note_count] = range(authors_note_ranges[authors_note_count].start, i)

                # Break out if we find a signature
                if signed_note_re.match(element_text):
                    break

                if len(author_note_ele_text.strip()) == 0:
                    empty_line_cnt += 1
                    if empty_line_cnt >= 4:
                        break
                else:
                    empty_line_cnt = 0

            authors_note_count += 1
        elif authors_ps_note_re.match(element_text) and len(authors_note_ranges) > 0:
            # Extend authors note range to include any P.S. lines
            for i, author_note_ele in enumerate(elements[chapter_index:], start=chapter_index):
                author_note_ele_text = author_note_ele.get_text()
                if len(author_note_ele_text.strip()) == 0:
                    empty_line_cnt += 1
                    if empty_line_cnt >= 3:
                        authors_note_ranges[-1] = range(authors_note_ranges[-1].start, i + 1)
                        break
                else:
                    empty_line_cnt = 0
    return authors_note_ranges


def ranges_overlap(r1: range, r2: range) -> bool:
    return r1.start > r2.start and r2.stop > r1.start or r1.start < r2.start and r1.stop > r2.start


def parse_chapter_content(soup: BeautifulSoup) -> dict:
    content = extract_chapter_content(soup)

    if content is None:
        msg = "Chapter content cannot be parsed from None"
        raise ValueError(msg)

    chapter_data = {}
    content_children = list(content.children)

    # Exclude last two lines which include the previous and next chapter links
    # content_lines: list[str] = [element.get_text() for element in content_children[:-2]]

    # Ignore Patreon locked chapters
    if len(content_children) < 10 and any(("Patreon" in ele.get_text() for ele in content_children[:9])):
        raise PatreonChapterError

    # Exclude fanart images, links, and credits at end of chapter from parsing
    fanart_credit_pattern = re.compile(
        r".*([Bb]luesky|[Dd]eviant[Aa]rt|[Ii]nstagram|[Kk]o-?[Ff]i|[Tt]witter|Portfolio:).*"
    )
    first_img_index = len(content_children)
    excluded_tags = ["img", "iframe"]
    for i, child in enumerate(reversed(content_children)):
        if type(child) is Tag and (
            any(child.select(tag) for tag in excluded_tags)
            or (fanart_credit_pattern.match(child.text) and match_links(child.text))
        ):
            first_img_index = len(content_children) - i
        # Only check the last 200 lines of the chapter
        if i > 100:
            break
    # content_lines = content_lines[
    #     : first_img_index - 4
    # ]  # include additional lines to catch any credit text before the first img or a tag

    content_children = content_children[: first_img_index - 4]

    pre_note_range = identify_pre_note_range(content_children)
    pre_note_elements = content_children[: pre_note_range.stop]

    authors_note_ranges = identify_authors_note_ranges(content_children)
    authors_note_lines = chain(
        "\n".join(ele.get_text().strip() for ele in content_children[r.start : r.stop] if ele.get_text().strip() != "")
        for r in authors_note_ranges
    )

    # Check for pre-note overlapping any authors notes
    if any(pre_note_range.stop > r.start for r in authors_note_ranges):
        msg = f"The pre-note overlaps (one of) the Authors' notes: {authors_note_ranges}"
        raise ChapterPartitionsOverlappingError(msg)

    # Check for any author's notes overlapping each other
    if any(ranges_overlap(r1, r2) for r1 in authors_note_ranges for r2 in authors_note_ranges):
        msg = f"Author's note ranges are overlapping: {authors_note_ranges}"
        raise ChapterPartitionsOverlappingError(msg)

    # Build chapter text based on line ranges for pre-note and author's note(s)
    match len(authors_note_ranges):
        case 0:
            chapter_elements = [ele for ele in content_children[pre_note_range.stop :] if ele.get_text().strip() != ""]
        case 1:
            chapter_elements = [
                ele
                for ele in chain(
                    content_children[pre_note_range.stop : authors_note_ranges[0].start - 1],
                    content_children[authors_note_ranges[0].stop :],
                )
                if ele.get_text().strip() != ""
            ]
        case 2:
            # Ensure chapter content between multiple authors notes is captured
            chapter_elements = [
                ele
                for ele in chain(
                    content_children[pre_note_range.stop : authors_note_ranges[0].start],
                    content_children[authors_note_ranges[0].stop + 1 : authors_note_ranges[1].start],
                )
                if ele.get_text().strip() != ""
            ]
        case _:
            raise TooManyAuthorsNotes

    pre_note_lines = [ele.get_text().strip() for ele in pre_note_elements if ele.get_text().strip() != ""]

    chapter_data["cleaned_html"] = "\n".join([str(e) for e in chapter_elements]) + "\n"
    chapter_data["text"] = "\n".join([e.get_text().strip() for e in chapter_elements]) + "\n"
    chapter_data["authors_note"] = "\n".join(authors_note_lines) + "\n"
    chapter_data["pre_note"] = "\n".join(pre_note_lines) + "\n"

    try:
        word_count = len(chapter_data["text"].split())

        authors_note_word_count = len(chapter_data["authors_note"].split())
        digest: str = hashlib.sha256(chapter_data["cleaned_html"].encode("utf-8")).hexdigest()
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
