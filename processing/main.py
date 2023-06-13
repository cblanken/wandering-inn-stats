import argparse
from pathlib import Path
from glob import glob
from processing import Chapter

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="innverse-processing",
        description="CLI for innverse processing module"
    )

    parser.add_argument("path", default="./data",
                         help="Path to volumes")
    args = parser.parse_args()

    paths = [Path(x) for x in glob(f"./{args.path}/*/*/*/*") if Path(x).is_dir()]
    for p in paths:
        chapter = Chapter(Path(p))
        chapter.print_bracket_refs()
