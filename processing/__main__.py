import argparse
from pathlib import Path
from . import Volume

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="innverse-processing",
        description="CLI for innverse processing module"
    )

    parser.add_argument("path", type=Path, help="Path to volumes")
    args = parser.parse_args()

    volume_paths = [x for x in Path(args.path).iterdir() if x.is_dir() and "Volume" in x.name]
    for p in volume_paths:
        vol = Volume(p.name.split('_')[1], p)
        print("")
        print(vol)
        for book in vol.books.values():
            print(book)
            for chapter in book.chapters.values():
                chapter.print_all_text_refs()
