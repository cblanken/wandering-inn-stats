"""Module to download every chapter from the links in the Wandering Inn Table of Contents"""
from sys import argv, stderr
from os import path, sep, getcwd, mkdir
from time import sleep
from requests import get
from bs4 import BeautifulSoup

BASE_URL = "https://wanderinginn.com/table-of-contents/"
BASE_PATH = "chapters"
if not path.isdir(BASE_PATH):
    mkdir(BASE_PATH)

class TableOfContents:
    """Object to scrape the Table of Contents and methods to query for any needed info
    """
    def __init__(self):
        self.url = "https://wanderinginn.com/table-of-contents/"
        table_of_contents = get(self.url)
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
                '#content div > p > a[href^="https://wanderinginn.com"]')
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

        chapter_index = 0
        chapter_indexes = []
        for chapter_list in chapter_lists:
            start = chapter_index
            end = start + len(chapter_list) - 1
            chapter_index = end + 1
            chapter_indexes.append( (start, end) )
        return chapter_indexes

def get_chapter_text(chapter_link):
    """Scrape chapter text from link
    """
    page = get(chapter_link)
    soup = BeautifulSoup(page.content, 'html.parser')
    header_text = [element.get_text() for element in soup.select(
        '#content > article > header.entry-header')]
    content_text = [element.get_text() for element in soup.select(
        '#content > article > div.entry-content > *')]
    return "".join(header_text) + "\n\n".join(content_text)

def save_chapter(file, content):
    """Write chapter text content to file
    """
    with open(file, "w", encoding="utf-8") as file:
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
    for i, link in enumerate(chapter_links[OFFSET:max_chapter]):
        file_prefix = f"{OFFSET + i}-"

        # remove trailing '/' from URL
        FILE_SUFFIX = str(link[8:-1]) if link[-1] == "/" else str(link[8:])

        filename = file_prefix + FILE_SUFFIX.replace(sep, '-')
        FILEPATH = sep.join([getcwd(), BASE_PATH, filename])
        if not path.exists(FILEPATH) and link is not None:
            print(f"Downloading {link} to {FILEPATH}")
            save_chapter(FILEPATH, get_chapter_text(link))
            sleep(0.25)
        else:
            print(f"Skipping {link}, {filename} already exists")
