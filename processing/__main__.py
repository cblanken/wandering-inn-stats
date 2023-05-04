import argparse
from pathlib import Path
from . import get_text_ref_generators_by_chapter_title, print_all_text_refs

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="innverse-processing",
        description="CLI for innverse processing module"
    )

    parser.add_argument("path", type=Path, help="Path to volumes")
    args = parser.parse_args()
    
    print_all_text_refs(Path(args.path))
