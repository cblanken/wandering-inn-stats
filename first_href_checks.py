import json
from stats.models import Chapter, Character, TextRef

def get_char_missing_first_href():
    with open("./data/characters.json", encoding="utf-8") as fp:
        data = json.load(fp)
        with open("./char_missing_first_href.csv", "w", encoding="utf-8") as fp:
            fp.write(f"Character,Wiki URL,Current First Chapter Ref URL,New First Chapter Ref URL\n")
            for i, (name, meta) in enumerate(data.items()):
                char = Character.objects.get(ref_type__name=name)
                if char.first_chapter_ref == None:
                    href = meta.get("first_href", "")
                    char_refs = TextRef.objects.filter(type__name=name).order_by("chapter__number")
                    
                    if char_refs.exists():
                        first_chapter = char_refs[0].chapter.source_url
                    else:
                        first_chapter = ""


                    fp.write(f"{name},{meta.get('wiki_href', '')},{href},{first_chapter}\n")
    