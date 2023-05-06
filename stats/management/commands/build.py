from pathlib import Path
from datetime import date
from django.core.management.base import BaseCommand, CommandError
from django.db import models
from stats.models import Color, Chapter, Book, Volume, TextRef, RefType
from processing import Volume as SrcVolume

def get_ref_type() -> str:
    """Interactive classification of TextRef type"""
    try:
        sel = input(
            f"Classify the above TextRef {RefType.TYPES} (leave blank to skip): "
        )

        while True:
            if sel.strip() == "":
                print("> TextRef skipped!\n")
                return None
            if len(sel) < 2:
                print("Invalid selection.")
                yes_no = input("Try again (y/n)")
                if yes_no.lower() == "y":
                    continue
                return None
            break

        match sel[:2].upper():
            case "CL":
                return RefType.CLASS
            case "CO":
                return RefType.CLASS_OBTAINED
            case "SK":
                return RefType.SKILL
            case "SO":
                return RefType.SKILL_OBTAINED
            case "SP":
                return RefType.SPELL
            case "SB":
                return RefType.SPELL_OBTAINED
            case "CH":
                return RefType.CHARACTER
            case "IT":
                return RefType.ITEM
            case "LO":
                return RefType.LOCATION
            case _:
                return None

    except KeyboardInterrupt as exc:
        print("")
        raise CommandError("Build interrupted with Ctrl-C (Keyboard Interrupt).") from exc
    except EOFError as exc:
        print("")
        raise CommandError("Build interrupted with Ctrl-D (EOF).") from exc


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
                print(f"> Record created: {volume}")
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
                    print(f"> Record created: {book}")
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
                        print(f"> Record created: {chapter}")
                        chapter.save()

                    for ref in src_chapter.all_text_refs:
                        print(ref)

                        try:
                            ref_type = RefType.objects.get(name=ref.text)
                            self.stdout.write(
                                self.style.WARNING(f"> RefType {ref.text} already exists. Skipping creation...")
                            )
                        except RefType.DoesNotExist:
                            ref_type = RefType(name=ref.text, type=get_ref_type())
                            ref_type.save()
                            print(f"> Record created: {ref_type}")

                        try:
                            text_ref = TextRef.objects.get(
                                chapter=chapter,
                                type=ref_type,
                                line_number=ref.line_number,
                                start_column=ref.start_column,
                            )
                            self.stdout.write(
                                self.style.WARNING(f"> TextRef {text_ref.text} already exists. Skipping creation...")
                            )
                        except TextRef.DoesNotExist:
                            text_ref = TextRef(
                                text=ref.text,
                                type=ref_type,
                                chapter=chapter,
                                line_number=ref.line_number,
                                start_column=ref.start_column,
                                end_column = ref.end_column,
                                context_offset = ref.context_offset,
                            )

                            text_ref.save()

                    num += 1

