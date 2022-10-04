"""Module to download every chapter from the links in the Wandering Inn Table of Contents"""
from sys import argv, stderr
from pathlib import Path
from time import sleep
from bs4 import BeautifulSoup
import requests

BASE_URL = "https://wanderinginn.com"
CHAPTERS_PATH = Path("./chapters")
CHAPTERS_TXT_PATH = Path(CHAPTERS_PATH, "text")
CHAPTERS_SRC_PATH = Path(CHAPTERS_PATH, "src")
CHAPTERS_TXT_PATH.mkdir(parents = True, exist_ok = True)
CHAPTERS_SRC_PATH.mkdir(parents = True, exist_ok = True)
REQUEST_THROTTLE_S = 1.0

class TableOfContents:
    """Object to scrape the Table of Contents and methods to query for any needed info
    """
    def __init__(self):
        self.url = "https://wanderinginn.com/table-of-contents/"
        table_of_contents = requests.get(self.url)
        if table_of_contents.status_code != 200:
            print(f"Cannot access {self.url}. Check your network connection.")
            return None
        self.soup = BeautifulSoup(table_of_contents.content, 'html.parser')
        self.chapter_links = self.get_chapter_links()
        self.volume_titles_by_id = self.get_volume_titles_by_id()

    def get_chapter_links(self):
        """Scrape table of contents for chapter links
        """
        chapter_link_elements = self.soup.select(
                f'#content div > p > a[href^="{BASE_URL}"]')
        return list(filter(None, [link.get('href') for link in chapter_link_elements]))

    def get_volume_titles_by_id(self):
        """Scrape table of contents volume titles
        """
        volume_titles = self.soup.select('#content div > p:nth-of-type(2n+1) strong')

        volumes = {}
        for ele in volume_titles:
            text = ele.get_text().strip()
            try:
                id = int(text[text.find(" "):])
                volumes[id] = text
            except ValueError:
                # TODO handle int parse error
                print("Failed to parse Volume ID from scraped table of contents", file=stderr)
                return None
        return volumes

    def get_volume_chapter_index_ranges(self):
        """Scrape table of contents for chapter indexes of each volume
        """
        chapter_lists = [
            x.find_all('a') for x in self.soup.select('#content div p:nth-of-type(2n)')
        ]

        volume_index = 1
        chapter_index = 1
        chapter_indexes = {}
        for chapter_list in chapter_lists:
            start = chapter_index
            end = start + len(chapter_list) - 1
            chapter_index = end + 1
            chapter_indexes[volume_index] = (start, end)
            volume_index += 1
        return chapter_indexes


def get_chapter(chapter_link):
    """Get HTML of chapter
    """
    try:
        return requests.get(chapter_link)
    except requests.HTTPError:
        print(f"Unable to retrieve chapter from {chapter_link}", file=stderr)
        return None

def get_chapter_text(html):
    """Scrape chapter text from link
    """
    soup = BeautifulSoup(html.content, 'html.parser')
    header_text = [element.get_text() for element in soup.select(
        '#content > article > header.entry-header')]
    content_text = [element.get_text() for element in soup.select(
        '#content > article > div.entry-content > *')]
    return "".join(header_text) + "\n\n".join(content_text)

def save_file(filepath, content):
    """Write chapter text content to file
    """
    with open(filepath, "w", encoding="utf-8") as file:
        file.write(content)

if __name__ == "__main__":
    toc = TableOfContents()
    chapter_links = toc.get_chapter_links()
    max_chapter = len(chapter_links)
    OFFSET = 0
    if len(argv) == 2:
        try:
            # Max offset of 1000
            OFFSET = min(int(argv[1]), 1000)
        except TypeError:
            print("Invalid offset argument. Enter a number between 1 and 1000.")
            exit(0)
    elif len(argv) > 2:
        try:
            # Max offset of 1000
            OFFSET = min(int(argv[1]), 1000)
            max_chapter = min(int(argv[2]), max_chapter)
        except TypeError:
            print("Invalid offset argument. Enter a number between 1 and 1000.")
            exit(0)

    # TODO handle keyboard interrupt
    # TODO add pause/resume
    # TODO add type hinting
    # TODO add chapter hashing to check for changes
    # TODO add chapter archiving functionality
    # TODO use urllib or requests to handle URLs
    # TODO add error handling
    for i, link in enumerate(chapter_links[OFFSET:max_chapter]):
        if link is None:
            print(f"No link provided in chapter_links[{i}]", file=stderr)
            continue

        file_prefix = f"{OFFSET + i + 1}-"

        # remove trailing '/' from URL and replace '/' with '-'
        FILE_SUFFIX = (str(link[8:-1]) if link[-1] == "/" else str(link[8:])).replace("/", "-")
        filename = file_prefix + FILE_SUFFIX

        src_path = Path(CHAPTERS_SRC_PATH, filename + ".html")
        txt_path = Path(CHAPTERS_TXT_PATH, filename + ".txt")

        if src_path.exists() or txt_path.exists():
            print(f"Skipping, {src_path} or {txt_path} already exists")
            continue

        print(f"{i}: Downloading {link}")
        HTML = get_chapter(link)
        TEXT = get_chapter_text(HTML)

        save_file(src_path, HTML.text)
        print(f"\t{link} src saved to {src_path}")

        save_file(txt_path, TEXT)
        print(f"\t{link} text saved to {txt_path}")

        sleep(REQUEST_THROTTLE_S)
