import json
from stats.models import Character, TextRef
from pathlib import Path


def get_char_missing_first_href():
    characters_path = Path("./data/characters.json")
    with characters_path.open(encoding="utf-8") as fp:
        data = json.load(fp)
        missing_chars_path = Path("./char_missing_first_href.csv")
        with missing_chars_path.open("w", encoding="utf-8") as fp:
            fp.write("Character,Wiki URL,Current First Chapter Ref URL,New First Chapter Ref URL\n")
            for _i, (name, meta) in enumerate(data.items()):
                char = Character.objects.get(ref_type__name=name)
                if char.first_chapter_appearance is None:
                    href = meta.get("first_href", "")
                    char_refs = TextRef.objects.filter(type__name=name).order_by("chapter__number")

                    if char_refs.exists():
                        first_chapter = char_refs[0].chapter_line.chapter.source_url
                    else:
                        first_chapter = ""

                    fp.write(f"{name},{meta.get('wiki_href', '')},{href},{first_chapter}\n")
