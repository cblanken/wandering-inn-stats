from pathlib import Path
from glob import glob
from django.core.management.base import BaseCommand, CommandError
from stats.models import Color, LevelingToken, Character, Chapter, Volume, TextRef
from processing import generate_chapter_text_refs
from processing.get import TableOfContents

class Command(BaseCommand):
    help = "Update database per chapter sources"

    def add_arguments(self, parser):
        parser.add_argument("chapters_path", nargs="?", type=str, default="../../../processing/chapters")

    def handle(self, *args, **options):
        self.stdout.write("Updating DB...")

        src_path = Path(options["chapters_path"], "src")
        txt_path = Path(options["chapters_path"], "txt")

        if not src_path.exists() or not txt_path.exists():
            raise CommandError("Chapters directory does not exist.")


        # Process chapter txt files
        txt_files_by_id = [
            {
                'id': int(Path(x).name.split('-')[0]),
                'path' : Path(x),
            } for x in glob(f"{txt_path}/*.txt")
        ]
        txt_files_by_id.sort(key = lambda n: n['id'])
        #for chapter in txt_files_by_id[:10]:
        #    print(f"---- {chapter}")
        #    for ref in generate_chapter_text_refs(chapter['path']):
        #        self.stdout.write(ref.text)

        toc = TableOfContents()
        for data in toc.get_volume_data():
            num = data[0].split(' ')[-1]
            print(Volume(number=num, title=data[0] ))

            for link in data[1]:
                print(link)
            

        breakpoint()

        ## Process chapter source html files
        #src_files_by_id = [(int(x.split('-')[0]), x) for x in os.listdir(src_path)]
        #src_files_by_id.sort()
        #for chapter in src_files_by_id:
        #    self.stdout.write(chapter[1])