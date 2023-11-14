from django.db import models


class ColorCategory(models.Model):
    """Model linking Colors to a their corresponding categories"""

    name = models.CharField(max_length=50, unique=True, verbose_name="Color")

    class Meta:
        verbose_name_plural = "Color Categories"

    def __str__(self):
        return f"(ColorCategory: {self.name})"


class Color(models.Model):
    """Model for colored text"""

    # TODO: add rgb regex constraint
    rgb = models.CharField(max_length=8)
    category = models.ForeignKey(
        ColorCategory, on_delete=models.CASCADE, verbose_name="Color Category"
    )

    class Meta:
        ordering = ["rgb"]

    def __str__(self):
        return f"(Color: {self.category.name}: {self.rgb})"


class Volume(models.Model):
    "Model for volumes"
    number = models.PositiveIntegerField(unique=True, verbose_name="Volume Number")
    title = models.CharField(max_length=50, unique=True, verbose_name="Volume Title")
    summary = models.TextField(default="")

    class Meta:
        ordering = ["number"]

    def __str__(self):
        return f"(Volume: {self.title}, Summary: {str(self.summary)[:30]}...)"


class Book(models.Model):
    "Model for books"
    number = models.PositiveBigIntegerField(verbose_name="Book Number")
    title = models.CharField(max_length=50, verbose_name="Book Title")
    volume = models.ForeignKey(Volume, on_delete=models.CASCADE)
    summary = models.TextField(default="")

    class Meta:
        ordering = ["volume", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["volume", "title"], name="unique_volume_and_title"
            )
        ]

    def __str__(self):
        return f"(Book: {self.title}, Summary: {str(self.summary)[:30]})"


class Chapter(models.Model):
    "Model for book chapters"
    number = models.PositiveBigIntegerField()
    title = models.CharField(max_length=50, verbose_name="Chapter Title")
    is_interlude = models.BooleanField()
    source_url = models.URLField()
    post_date = models.DateTimeField()
    last_update = models.DateTimeField()
    download_date = models.DateTimeField()
    word_count = models.PositiveBigIntegerField(default=0)
    authors_note_word_count = models.PositiveBigIntegerField(default=0)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)

    class Meta:
        ordering = ["number"]

    def __str__(self) -> str:
        return f"(Chapter: {self.title}, URL: {self.source_url})"


class RefType(models.Model):
    """Reference keywords / phrases"""

    CHARACTER = "CH"
    CLASS = "CL"
    CLASS_OBTAINED = "CO"
    ITEM = "IT"
    LOCATION = "LO"
    MIRACLE = "MI"
    SKILL = "SK"
    SKILL_OBTAINED = "SO"
    SPELL = "SP"
    SPELL_OBTAINED = "SB"
    TYPES = [
        (CHARACTER, "Character"),
        (CLASS, "Class"),
        (CLASS_OBTAINED, "Class Obtained"),
        (ITEM, "Item"),
        (LOCATION, "Location"),
        (MIRACLE, "Miracle"),
        (SKILL, "Skill"),
        (SKILL_OBTAINED, "Skill Obtained"),
        (SPELL, "Spell"),
        (SPELL_OBTAINED, "Spell Obtained"),
    ]
    name = models.CharField(max_length=120)
    type = models.CharField(max_length=2, choices=TYPES, null=True)
    description = models.CharField(max_length=120, default="")
    is_divine = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Ref Types"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "type"], name="unique_name_and_type"
            )
        ]

    def __str__(self):
        return (
            f"(RefType: {self.name} - Type: {self.type}, is_divine: {self.is_divine})"
        )


class Character(models.Model):
    """Character data"""

    # Unspecified or unclear status/species
    UNKNOWN = "UK"

    # Species short-codes
    AGELUM = "AG"
    ANTINIUM = "AN"
    BEASTKIN = "BK"
    CENTAUR = "CT"
    CYCLOPS = "CY"
    DEMON = "DE"
    DRAGON = "DG"
    DRAKE = "DR"
    DROWNED_PEOPLE = "DP"
    DRYAD = "DY"
    DULLAHAN = "DU"
    ELF = "EL"
    FAE = "FA"
    FRAERLING = "FR"
    GARUDA = "GR"
    GAZER = "GA"
    GOBLIN = "GB"
    GOD = "GO"
    GOLEM = "GM"
    HALFLING = "HA"
    HALF_ELF = "HE"
    HALF_GAZER = "HG"
    HALF_TROLL = "HT"
    HARPY = "HR"
    HUMAN = "HU"
    KELPIES = "KE"
    KITSUNE = "KI"
    LIZARDFOLK = "LF"
    LIZARDFOLK_GORGON = "LG"
    LIZARDFOLK_INDISHEI = "LI"
    LIZARDFOLK_LAMIA = "LL"
    LIZARDFOLK_MEDUSA = "LM"
    LIZARDFOLK_NAGA = "LN"
    LIZARDFOLK_QUEXAL = "LQ"
    LIZARDFOLK_SCYLLA = "LS"
    LIZARDFOLK_STAR_LAMIA = "LS"
    LIZARDFOLK_TASGIEL = "LT"
    LUCIFEN = "LU"
    MERFOLK = "ME"
    MINOTAUR = "MI"
    OGRE = "OG"
    PHOENIX = "PH"
    SARIANT_LAMB = "SL"
    SELPHID = "SE"
    SPIDERFOLK = "SF"
    STRING_PEOPLE = "SP"
    TITAN = "TI"
    TREANT = "TR"
    TROLL = "TL"
    UNDEAD = "UD"
    UNICORN = "UC"
    VAMPIRE = "VA"
    WYRM = "WY"
    WYVERN = "WV"

    SPECIES = [
        (AGELUM, "Agelum"),
        (ANTINIUM, "Antinium"),
        (BEASTKIN, "Beastkin"),
        (CENTAUR, "Centaur"),
        (CYCLOPS, "Cyclops"),
        (DEMON, "Demon"),
        (DRAGON, "Dragon"),
        (DROWNED_PEOPLE, "Drowned People"),
        (DRAKE, "Drake"),
        (DULLAHAN, "Dullahan"),
        (DRYAD, "Dryad"),
        (ELF, "Elf"),
        (FAE, "Fae"),
        (FRAERLING, "Fraerling"),
        (GAZER, "Gazer"),
        (GOBLIN, "Goblin"),
        (GOLEM, "Golem"),
        (GOD, "God"),
        (GARUDA, "Garuda"),
        (HALFLING, "Halfling"),
        (HALF_ELF, "Half-Elf"),
        (HALF_GAZER, "Half-Gazer"),
        (HALF_TROLL, "Half-Troll"),
        (HARPY, "Harpy"),
        (HUMAN, "Human"),
        (KELPIES, "Kelpies"),
        (KITSUNE, "Kitsune"),
        (LIZARDFOLK, "Lizardfolk"),
        (LIZARDFOLK_GORGON, "Lizardfolk - Gorgon"),
        (LIZARDFOLK_INDISHEI, "Lizardfolk - Indishei"),
        (LIZARDFOLK_LAMIA, "Lizardfolk - Lamia"),
        (LIZARDFOLK_MEDUSA, "Lizardfolk - Medusa"),
        (LIZARDFOLK_NAGA, "Lizardfolk - Naga"),
        (LIZARDFOLK_QUEXAL, "Lizardfolk - Quexal"),
        (LIZARDFOLK_SCYLLA, "Lizardfolk - Scylla"),
        (LIZARDFOLK_STAR_LAMIA, "Lizardfolk - Star Lamia"),
        (LIZARDFOLK_TASGIEL, "Lizardfolk - Tasgiel"),
        (LUCIFEN, "Lucifen"),
        (MERFOLK, "Merfolk"),
        (MINOTAUR, "Minotaur"),
        (OGRE, "Ogre"),
        (PHOENIX, "Phoenix"),
        (SELPHID, "Selphid"),
        (SPIDERFOLK, "Spiderfolk"),
        (SARIANT_LAMB, "Sariant Lamb"),
        (STRING_PEOPLE, "String People"),
        (TITAN, "Titan"),
        (TROLL, "Troll"),
        (TREANT, "Treant"),
        (UNDEAD, "Undead"),
        (UNICORN, "Unicorn"),
        (VAMPIRE, "Vampire"),
        (WYVERN, "Wyvern"),
        (WYRM, "Wyrm"),
        (UNKNOWN, "Unknown"),
    ]

    # Status short-codes
    ALIVE = "AL"
    DEAD = "DE"

    STATUSES = [
        (ALIVE, "Alive"),
        (DEAD, "Deceased"),
        (UNDEAD, "Undead"),
        (UNKNOWN, "Unknown"),
    ]

    ref_type = models.ForeignKey(RefType, on_delete=models.CASCADE)
    first_chapter_appearance = models.ForeignKey(
        Chapter, on_delete=models.CASCADE, null=True
    )
    wiki_uri = models.URLField(null=True)
    status = models.CharField(max_length=2, choices=STATUSES, null=True)
    species = models.CharField(max_length=2, choices=SPECIES, null=True)

    # TODO: correctly parse poorly formatted alternates instead
    # of lumping into UNKNOWN
    def parse_status_str(s: str):
        if s is None:
            return Character.UNKNOWN
        match s.strip():
            case "Alive" | "alive":
                return Character.ALIVE
            case "Deceased" | "deceased" | "Dead" | "dead":
                return Character.DEAD
            case "Undead" | "undead":
                return Character.UNDEAD
            case "Unknown" | "unknown" | "Unclear" | "unclear":
                return Character.UNKNOWN
            case _:
                return Character.UNKNOWN

    def parse_species_str(s: str):
        if s is None:
            return Character.UNKNOWN

        match s.strip().lower():
            case "agelum":
                return Character.AGELUM
            case "antinium":
                return Character.ANTINIUM
            case "beastkin":
                return Character.BEASTKIN
            case "centaur":
                return Character.CENTAUR
            case "cyclops":
                return Character.CYCLOPS
            case "demon":
                return Character.DEMON
            case "dragon":
                return Character.DRAGON
            case "drowned":
                return Character.DROWNED_PEOPLE
            case "drake" | "oldblood drake":
                return Character.DRAKE
            case "dullahan":
                return Character.DULLAHAN
            case "dryad":
                return Character.DRYAD
            case "elf":
                return Character.ELF
            case "fae":
                return Character.FAE
            case "fraerling":
                return Character.FRAERLING
            case "gazer":
                return Character.GAZER
            case "goblin":
                return Character.GOBLIN
            case "golem":
                return Character.GOLEM
            case "god":
                return Character.GOD
            case "garuda":
                return Character.GARUDA
            case "halfling":
                return Character.HALFLING
            case "half-elf":
                return Character.HALF_ELF
            case "half-gazer":
                return Character.HALF_GAZER
            case "harpy":
                return Character.HARPY
            case "half-troll":
                return Character.HALF_TROLL
            case "human":
                return Character.HUMAN
            case "kelpies" | "kelpy":
                return Character.KELPIES
            case "kitsune":
                return Character.KITSUNE
            case "lizardfolk" | "lizard-folk":
                return Character.LIZARDFOLK
            case "lizardfolk (gorgon)" | "gorgon":
                return Character.LIZARDFOLK_GORGON
            case "lizardfolk (indishei)" | "indishei":
                return Character.LIZARDFOLK_INDISHEI
            case "lizardfolk (lamia)" | "lamia":
                return Character.LIZARDFOLK_LAMIA
            case "lizardfolk (medusa)" | "medusa":
                return Character.LIZARDFOLK_MEDUSA
            case "lizardfolk (naga)" | "naga":
                return Character.LIZARDFOLK_NAGA
            case "lizardfolk (quexal)" | "quexal":
                return Character.LIZARDFOLK_QUEXAL
            case "lizardfolk (scylla)" | "scylla":
                return Character.LIZARDFOLK_SCYLLA
            case "lizardfolk (star lamia)" | "star lamia" | "star-lamia":
                return Character.LIZARDFOLK_STAR_LAMIA
            case "lizardfolk (tasgiel)" | "tasgiel":
                return Character.LIZARDFOLK_TASGIEL
            case "lucifen":
                return Character.LUCIFEN
            case "merfolk":
                return Character.MERFOLK
            case "minotaur":
                return Character.MINOTAUR
            case "ogre":
                return Character.OGRE
            case "phoenix":
                return Character.PHOENIX
            case "selphid":
                return Character.SELPHID
            case "spiderfolk" | "spider-folk":
                return Character.SPIDERFOLK
            case "sariant lamb" | "sariant":
                return Character.SARIANT_LAMB
            case "string people" | "string person" | "string-person":
                return Character.STRING_PEOPLE
            case "titan":
                return Character.TITAN
            case "troll":
                return Character.TROLL
            case "treant":
                return Character.TREANT
            case "undead":
                return Character.UNDEAD
            case "unicorn":
                return Character.UNICORN
            case "vampire":
                return Character.VAMPIRE
            case "wyvern":
                return Character.WYVERN
            case "wyrm":
                return Character.WYRM
            case _:
                return Character.UNKNOWN

    def __str__(self) -> str:
        return f"(Character: {self.ref_type.name}, Status: {self.status}, Species: {self.species})"


class Item(models.Model):
    ref_type = models.ForeignKey(RefType, on_delete=models.CASCADE)
    first_chapter_ref = models.ForeignKey(Chapter, on_delete=models.CASCADE, null=True)
    wiki_uri = models.URLField(null=True)

    def __str__(self) -> str:
        return f"(Item: {self.ref_type.name}, Wiki: {self.wiki_uri})"


class Location(models.Model):
    ref_type = models.ForeignKey(RefType, on_delete=models.CASCADE)
    first_chapter_ref = models.ForeignKey(Chapter, on_delete=models.CASCADE, null=True)
    wiki_uri = models.URLField(null=True)

    def __str__(self) -> str:
        return f"(Location: {self.ref_type.name}, Wiki: {self.wiki_uri})"


class Skill(models.Model):
    ref_type = models.ForeignKey(RefType, on_delete=models.CASCADE)
    first_chapter_ref = models.ForeignKey(Chapter, on_delete=models.CASCADE, null=True)
    wiki_uri = models.URLField(null=True)

    def __str__(self) -> str:
        return f"(Skill: {self.ref_type.name}, Wiki: {self.wiki_uri})"


class Spell(models.Model):
    ref_type = models.ForeignKey(RefType, on_delete=models.CASCADE)
    first_chapter_ref = models.ForeignKey(Chapter, on_delete=models.CASCADE, null=True)
    wiki_uri = models.URLField(null=True)

    def __str__(self) -> str:
        return f"(Spell: {self.ref_type.name}, Wiki: {self.wiki_uri})"


class Alias(models.Model):
    """RefType aliases / alternate names"""

    name = models.CharField(unique=True, max_length=100)
    ref_type = models.ForeignKey(RefType, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Aliases"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"(Alias: {self.name} - RefType: {self.ref_type})"


class ChapterLine(models.Model):
    """Chapter text content by line"""

    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE)
    line_number = models.PositiveIntegerField()
    text = models.TextField()

    class Meta:
        verbose_name_plural = "Chapter Lines"
        ordering = ["chapter", "line_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["chapter", "line_number"], name="unique_chapter_and_line"
            )
        ]

    def __str__(self):
        return f"(Chapter: ({self.chapter.number}) {self.chapter.title}, Line: {self.line_number}, Text: {self.text})"


class TextRef(models.Model):
    """Instances of Ref(s) found in text"""

    chapter_line = models.ForeignKey(ChapterLine, on_delete=models.CASCADE)
    type = models.ForeignKey(RefType, on_delete=models.CASCADE)
    color = models.ForeignKey(Color, on_delete=models.PROTECT, null=True)
    start_column = models.PositiveIntegerField()
    end_column = models.PositiveIntegerField()

    class Meta:
        verbose_name_plural = "Text Refs"
        ordering = ["chapter_line__chapter"]
        constraints = [
            models.UniqueConstraint(
                name="key",
                fields=["chapter_line", "start_column", "end_column"],
            )
        ]

    def __str__(self):
        return f"(TextRef: {self.type}, line: {self.chapter_line.line_number:>5}, start: {self.start_column:>4}, end: {self.end_column:>4})"
