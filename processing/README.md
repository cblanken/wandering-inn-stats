# The Wandering Inn Scraping
The `processing` module parses [The Wandering Inn](https://wanderinginn.com/) table of
contents for the links to all the chapters and downloads them. All chapters contents are
saved to `./chapters` by default.

There is also a helper script (`link_volumes.sh`) provided to organize all the downloaded
chapters into their respective volumes via symbolic link.

The scraper accepts two arguments
1. An offset or starting chapter id
2. A maximum id

## Usage
```console
$ python get.py         # download all chapters
$ python get.py 0 200   # download the first 200 chapters
$ python get.py 200 500 # download chapters 200 to 500
```

NOTE: the website will IP block the scraper after downloading a couple hundred chapters,
so you may want to increase the default throttle time or download chapters in smaller
batches.
