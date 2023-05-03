import argparse
from pathlib import Path
from . import print_all_text_refs

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="innverse-processing",
        description="CLI for innverse processing module"
    )

    parser.add_argument("path", help="Path to volumes")
    args = parser.parse_args()
    
    # TODO add table of contents fallback file
    print_all_text_refs(Path(args.path))
    # for (i, path) in chapter_paths:
    #     with open(path, encoding="utf-8") as fp:
    #         soup = BeautifulSoup(fp)
    #directory     id = int(path[:path.find("-")])