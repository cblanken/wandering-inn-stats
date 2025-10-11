from bs4 import BeautifulSoup
from itertools import islice
from stats.models import ChapterLine
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Database command to update ChapterLine plaintext fields"""

    help = "Update ReftypeChapter DB view"

    def handle(self, *_args, **_options) -> None:  # noqa: ANN002, ANN003
        empty_lines = iter(ChapterLine.objects.filter(text_plain="").values_list("pk", flat=True))
        batch_size = 2500
        while ids := list(islice(empty_lines, batch_size)):
            batch = ChapterLine.objects.filter(pk__in=ids)
            for cl in batch:
                plaintext = BeautifulSoup(cl.text).text
                cl.text_plain = plaintext
            ChapterLine.objects.bulk_update(batch, ["text_plain"], batch_size=batch_size)
            self.stdout.write(f"Updated...{batch[0]} to {batch[len(batch) - 1]}")

        self.stdout.write("Done.")
