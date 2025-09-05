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
from stem import Signal
from stem.control import Controller
from fake_useragent import UserAgent
from .exceptions import PatreonChapterError
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
    """Session object to download webpages via requests
    Also handles cycling Tor connections to prevent IP bans
    """

    def __init__(
        self,
        proxy_ip: str = "127.0.0.1",
        proxy_port: int = 9050,
        max_tries: int = 10,
        tor_enabled: bool = False,
        throttle: float = 2.0,
    ) -> None:
        print("> Connecting to session...")
        self.__session = requests.session()
        self.__proxy_port = proxy_port
        self.__tries = 0  # resets after a sucessful chapter download
        self.__max_tries = max_tries
        self.__tor_enabled = tor_enabled
        self.__throttle = throttle
        self.__last_get = 0
        if tor_enabled:
            self.set_tor_proxy(proxy_ip)

    def get(self, url: str, timeout: int = 10, ignore_throttle: bool = False) -> requests.Response | None:
        """Perform a GET request to [url]"""
        resp = None
        # Add jitter to throttle time
        throttle = random.uniform(0.5, 1.5) * self.__throttle
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
                if self.__tor_enabled:
                    print("Get new tor circuit", time.time())
                    self.get_new_tor_circuit()
            else:
                self.__tries = 0
                return resp

        print("Cannot re-attempt download. Too many retries. Must reset to continue.")
        return None

    def reset_tries(self) -> None:
        self.__tries = 0

    def set_tor_proxy(self, ip: str) -> None:
        self.__session.proxies = {
            "http": f"socks5://{ip}:{self.__proxy_port}",
            "https": f"socks5://{ip}:{self.__proxy_port}",
        }

    def get_new_tor_circuit(self, control_port: int = 9051) -> None:
        with Controller.from_port(port=control_port) as controller:
            controller.authenticate()
            controller.signal(Signal.NEWNYM)
            time.sleep(controller.get_newnym_wait())


def extract_chapter_content(soup: BeautifulSoup) -> Tag:
    content = soup.select_one(".entry-content")
    if content is None:
        msg = "The Chapter soup contains no .entry-content"
        raise ValueError(msg)

    return content


def parse_chapter_content(soup: BeautifulSoup) -> dict:
    content = extract_chapter_content(soup)

    if content is None:
        msg = "Chapter content cannot be parsed from None"
        raise ValueError(msg)

    chapter_data = {}

    # Exclude last two lines which include the previous and next chapter links
    content_lines: list[str] = [element.get_text() for element in content.children][:-2]

    authors_note_re = re.compile(r"Author['|’]s [N|n]ote.*")
    parens_pre_note_start_re = re.compile(r"^\(.*")
    parens_pre_note_end_re = re.compile(r".*\)$")
    signed_pre_note_re = re.compile(r".*[Pp]irateaba")
    chapter_lines = []
    authors_note_lines = []
    pre_note_lines = []

    chapter_index = 0
    while chapter_index < len(content_lines):
        chapter_line = content_lines[chapter_index]

        # Capture parenthesized chapter pre-note
        if chapter_index < 10 and parens_pre_note_start_re.match(chapter_line):
            # Check current and next few lines for completion of parens
            for i in range(5):
                if parens_pre_note_end_re.match(content_lines[chapter_index + i]):
                    pre_note_lines.append("\n".join(content_lines[chapter_index : chapter_index + i + 1]) + "\n")
                    chapter_index += i
                    break

            chapter_index += 1
            continue

        # Capture signed chapter pre-note
        if chapter_index < 10 and any(signed_pre_note_re.match(line) for line in chapter_line.split("\n")):
            pre_note_lines.extend(content_lines[: chapter_index + 1])
            chapter_lines.clear()
            chapter_index += 1
            continue

        # Capture note marked "Author's Note"
        if authors_note_re.match(content_lines[chapter_index].strip()):
            empty_line_cnt = 0
            for authors_note_index, author_note_line in enumerate(content_lines[chapter_index:]):
                if len(author_note_line.strip()) == 0:
                    empty_line_cnt += 1

                    if empty_line_cnt >= 2:
                        authors_note_lines = content_lines[chapter_index : chapter_index + authors_note_index]
                        break
                else:
                    empty_line_cnt = 0

            if chapter_index > int(len(content_lines) * 0.9):
                break
            chapter_index += authors_note_index

        else:
            if content_lines[chapter_index].strip() != "":
                chapter_lines.append(content_lines[chapter_index])

        chapter_index += 1

    chapter_data["text"] = "\n".join([line.strip() for line in chapter_lines]).strip() + "\n"
    chapter_data["authors_note"] = (
        "\n".join([line.strip() for line in authors_note_lines if line.strip() != ""]).strip() + "\n"
    )
    chapter_data["pre_note"] = "\n".join([line.strip() for line in pre_note_lines if line.strip() != ""]).strip() + "\n"

    try:
        word_count = len(chapter_data["text"].split())
        if word_count < 30 and "Patreon" in chapter_data["text"]:
            raise PatreonChapterError

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
