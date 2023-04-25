"""Module to download every chapter from the links in the Wandering Inn Table of Contents"""
from sys import argv, stderr
from pathlib import Path
from time import sleep
from bs4 import BeautifulSoup
import requests
import models

CHAPTERS_PATH = Path("./chapters")
CHAPTERS_TXT_PATH = Path(CHAPTERS_PATH, "text")
CHAPTERS_SRC_PATH = Path(CHAPTERS_PATH, "src")
CHAPTERS_TXT_PATH.mkdir(parents = True, exist_ok = True)
CHAPTERS_SRC_PATH.mkdir(parents = True, exist_ok = True)
REQUEST_THROTTLE_S = 1.0

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
    toc = models.TableOfContents()
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

        # Skip already downloaded chapters
        if src_path.exists() or txt_path.exists():
            continue

        print(f"{i}: Downloading {link}")
        HTML = get_chapter(link)
        TEXT = get_chapter_text(HTML)

        save_file(src_path, HTML.text)
        print(f"\t{link} src saved to {src_path}")

        save_file(txt_path, TEXT)
        print(f"\t{link} text saved to {txt_path}")

        sleep(REQUEST_THROTTLE_S)
