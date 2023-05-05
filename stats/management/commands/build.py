from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import models
from stats.models import Color, LevelingToken, Character, Chapter, Book, Volume, TextRef
from processing import Volume as SrcVolume, Color as SrcColor, RefType
from datetime import date

class Command(BaseCommand):
    help = "Update database from chapter source HTML and text files"

    def add_arguments(self, parser):
        parser.add_argument("volumes_path", type=str,
            help="Path in file system where chapter data is saved to disk per volume")

    def handle(self, *args, **options):
        self.stdout.write("Updating DB...")

        vol_root = Path(options["volumes_path"])
        volume_paths = [x for x in Path(vol_root).iterdir() if x.is_dir() and "Volume" in x.name]

        for path in volume_paths:
            src_vol: SrcVolume = SrcVolume(path.name.split('_')[1], path)
            print("")
            print(f"{src_vol} found")

            try:
                volume = Volume.objects.get(title=src_vol.title)
                self.stdout.write(
                    self.style.WARNING(f"> {src_vol.title} already exists. Skipping creation...")
                )
            except Volume.DoesNotExist:
                volume = Volume(number=int(src_vol.title.split(' ')[-1]), title=src_vol.title)
                print(f"{volume} record created")
                volume.save()

            for src_book in src_vol.books.values():
                try:
                    num = int(src_book.title.split(':')[0].split(' ')[-1])
                    book = Book.objects.get(title=src_book.title)
                    self.stdout.write(
                        self.style.WARNING(f"> {src_book.title} already exists. Skipping creation...")
                    )
                except Book.DoesNotExist:
                    book = Book(number=num, title=src_book.title, volume=volume)
                    print(f"{book} record created")
                    book.save()

                num = 1
                for src_chapter in src_book.chapters.values():
                    try:
                        chapter = Chapter.objects.get(title=src_chapter.title)
                        self.stdout.write(
                            self.style.WARNING(f"> {src_chapter.title} already exists. Skipping creation...")
                        )
                    except Chapter.DoesNotExist:
                        # TODO: update source_url and date properties
                        chapter = Chapter(
                            number=num, title=src_chapter.title, source_url="https://www.wanderinginn.com",
                            book=book, is_interlude="interlude" in src_chapter.title.lower(),
                            post_date=date.today)
                        print(f"{chapter} record created")
                        chapter.save()

                    num += 1
