from django.contrib.postgres.fields import ArrayField
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Length
from django.utils.text import slugify
import re
from typing import Any

models.CharField.register_lookup(Length, "length")


class ColorCategory(models.Model):
    """Model linking Colors to a their corresponding categories"""

    name = models.CharField(max_length=50, unique=True, verbose_name="Color")

    class Meta:
        verbose_name_plural = "Color Categories"

    def __str__(self):
        return f"(ColorCategory: {self.name})"


class Color(models.Model):
    """Model for colored text"""

    rgb = models.CharField(
        max_length=6,
        validators=[RegexValidator(r"^[a-zA-Z\d]{6}$")],
    )
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
    title = models.TextField(unique=True, verbose_name="Volume Title")
    summary = models.TextField(default="")

    class Meta:
        ordering = ["number"]

    def __str__(self):
        return f"(Volume: {self.title}, Summary: {str(self.summary)[:30]}...)"


class Book(models.Model):
    "Model for books"
    number = models.PositiveBigIntegerField(verbose_name="Book Number")
    title = models.TextField(verbose_name="Book Title")
    volume = models.ForeignKey(Volume, on_delete=models.CASCADE)
    summary = models.TextField(default="")

    title_short = models.GeneratedField(  # type: ignore[attr-defined]
        expression=models.Func(
            models.Func(
                models.F("title"),
                models.Value(r"(\w+\s\w+)\s"),
                function="regexp_substr",
            ),
            function="trim",
        ),
        output_field=models.TextField(),
        db_persist=True,
    )

    class Meta:
        ordering = ["volume", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["volume", "title"], name="unique_volume_and_title"
            ),
            models.UniqueConstraint(
                fields=["volume", "number"], name="unique_volume_and_book_num"
            ),
        ]

    def __str__(self):
        return f"(Book: {self.title}, Summary: {str(self.summary)[:30]})"


class Chapter(models.Model):
    "Model for book chapters"
    number = models.PositiveBigIntegerField(unique=True)
    title = models.TextField(verbose_name="Chapter Title", unique=True)
    is_interlude = models.BooleanField()
    is_canon = models.BooleanField(default=True)
    is_status_update = models.BooleanField(default=False)
    source_url = models.URLField()
    post_date = models.DateTimeField()
    last_update = models.DateTimeField()
    download_date = models.DateTimeField()
    word_count = models.PositiveBigIntegerField(default=0)
    authors_note_word_count = models.PositiveBigIntegerField(default=0)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)

    title_short = models.GeneratedField(  # type: ignore[attr-defined]
        expression=models.Func(
            models.F("title"),
            models.Value(r"^Interlude"),
            models.Value(r"I."),
            function="regexp_replace",
        ),
        output_field=models.TextField(),
        db_persist=True,
    )

    class Meta:
        ordering = ["number"]
        indexes = [
            models.Index(fields=["number"]),
        ]

    def __str__(self) -> str:
        return f"(Chapter: {self.title}, URL: {self.source_url})"


class RefType(models.Model):
    """Reference keywords / phrases"""

    CHARACTER = "CH"
    CLASS = "CL"
    CLASS_UPDATE = "CO"
    CONDITION = "CN"
    ITEM = "IT"
    LOCATION = "LO"
    MIRACLE = "MI"
    MAGICAL_CHAT = "MC"
    SKILL = "SK"
    SKILL_UPDATE = "SO"
    SPELL = "SP"
    SPELL_UPDATE = "SB"
    SYSTEM_GENERAL = "SG"
    UNDECIDED = "IN"
    TYPES = [
        (CHARACTER, "Character"),
        (CLASS, "Class"),
        (CLASS_UPDATE, "Class Update"),
        (CONDITION, "Condition Update"),
        (ITEM, "Items and Artifacts"),
        (LOCATION, "Location"),
        (MIRACLE, "Miracle"),
        (MAGICAL_CHAT, "Magical Chat"),
        (SKILL, "Skill"),
        (SKILL_UPDATE, "Skill Update"),
        (SPELL, "Spell"),
        (SPELL_UPDATE, "Spell Update"),
        (SYSTEM_GENERAL, "System General"),
        (UNDECIDED, "Undecided"),
    ]
    name = models.TextField()
    type = models.CharField(max_length=2, choices=TYPES, null=True)
    slug = models.TextField(default="")
    word_count = models.GeneratedField(  # type: ignore[attr-defined]
        expression=models.Func(
            models.Func(
                models.F("name"), models.Value(r"\s+"), function="regexp_split_to_array"
            ),
            1,
            function="array_length",
        ),
        output_field=models.IntegerField(),
        db_persist=True,
    )
    letter_count = models.GeneratedField(  # type: ignore[attr-defined]
        expression=models.Func(
            "name", arity=1, function="length", output_field=models.IntegerField()
        ),
        output_field=models.IntegerField(),
        db_persist=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "type"], name="unique_name_and_type"
            )
        ]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["type"]),
        ]
        ordering = ["name"]
        verbose_name_plural = "Ref Types"

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name[:100], allow_unicode=True)
        super(RefType, self).save(*args, **kwargs)

    def delete(self):
        computed_cols = RefTypeComputedView.objects.filter(ref_type=self)
        for row in computed_cols:
            row.delete()

    def __str__(self):
        return f"(RefType: {self.name} - Type: {self.type})"


class Character(models.Model):
    """Character data"""

    # Unspecified or unclear status/species
    UNKNOWN = "UK"

    # Species short-codes
    AGELUM = "AG"
    ANTINIUM = "AN"
    ASHFIRE_BEE = "AB"
    BEASTKIN = "BK"
    BEASTKIN_BEAR = "BB"
    BEASTKIN_CAT = "BC"
    BEASTKIN_DOG = "BD"
    BEASTKIN_FALCON = "BF"
    BEASTKIN_FOX = "BX"
    BEASTKIN_JACKAL = "BJ"
    BEASTKIN_OWL = "BO"
    BEASTKIN_RABBIT = "BR"
    BEASTKIN_RHINO = "BH"
    BEASTKIN_SALAMANDER = "BS"
    BEASTKIN_SQUIRREL = "BQ"
    BEASTKIN_WOLF = "BW"
    CAT = "CA"
    CENTAUR = "CT"
    CYCLOPS = "CY"
    DEMON = "DE"
    DJINNI = "DJ"
    DRAGON = "DG"
    DRAKE = "DR"
    DROWNED_PEOPLE = "DP"
    DRYAD = "DY"
    DWARF = "DW"
    DULLAHAN = "DU"
    ELF = "EL"
    ELEMENTAL = "EM"
    FAE = "FA"
    FRAERLING = "FR"
    GARUDA = "GR"
    GAZER = "GA"
    GIANT = "GI"
    GOBLIN = "GB"
    GNOLL = "GN"
    GOD = "GO"
    GOLEM = "GM"
    GRIFFIN = "GR"
    HALFLING = "HA"
    HALF_ELF = "HE"
    HALF_GAZER = "HG"
    HALF_GIANT = "HI"
    HALF_TROLL = "HT"
    HARPY = "HR"
    HUMAN = "HU"
    KELPIES = "KE"
    KITSUNE = "KI"
    LIVING_ARMOR = "LA"
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
    MIMIC = "MM"
    MIND = "MN"
    MINOTAUR = "MI"
    OGRE = "OG"
    PEGASIS = "PG"
    PHOENIX = "PH"
    RASKGHAR = "RG"
    RAT = "RA"
    REVENANT = "RE"
    SARIANT_LAMB = "SL"
    SCORCHLING = "SH"
    SEAMWALKER = "SW"
    SELPHID = "SE"
    SLIME = "SL"
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

    # fmt: off
    SPECIES_DATA: list[tuple[str, str, re.Pattern[Any]]] = [
        (AGELUM, "Agelum", re.compile(r"[Aa]gelum")),
        (ANTINIUM, "Antinium", re.compile(r"[Aa]ntinium")),
        (ASHFIRE_BEE, "Ashfire Bee", re.compile(r"[Aa]shfire[-\s]?[Bb]ee")),
        (BEASTKIN, "Beastkin", re.compile(r"[Bb]eastkin")),
        (BEASTKIN_BEAR, "Beastkin - Bear", re.compile(r"[Bb]eastkin.*[Bb]ear")),
        (BEASTKIN_CAT, "Beastkin - Cat", re.compile(r"[Bb]eastkin.*[Cc]at")),
        (BEASTKIN_DOG, "Beastkin - Dog", re.compile(r"[Bb]eastkin.*[Dd]og")),
        (BEASTKIN_FALCON, "Beastkin - Falcon", re.compile(r"[Bb]eastkin.*[Ff]alcon")),
        (BEASTKIN_FOX, "Beastkin - Fox", re.compile(r"[Bb]eastkin.*[Ff]ox")),
        (BEASTKIN_JACKAL, "Beastkin - Jackal", re.compile(r"[Bb]eastkin.*[Jj]ackal")),
        (BEASTKIN_OWL, "Beastkin - Owl", re.compile(r"[Bb]eastkin.*[Oo]wl")),
        (BEASTKIN_RABBIT, "Beastkin - Rabbit", re.compile(r"[Bb]eastkin.*[Rr]abbit")),
        (BEASTKIN_RHINO, "Beastkin - Rhino", re.compile(r"[Bb]eastkin.*[Rr]hino.*")),
        (BEASTKIN_SALAMANDER, "Beastkin - Salamander", re.compile(r"[Bb]eastkin.*[Ss]alamander")),
        (BEASTKIN_SQUIRREL, "Beastkin - Squirrel", re.compile(r"[Bb]eastkin.*[Ss]quirrel")),
        (BEASTKIN_WOLF, "Beastkin - Wolf", re.compile(r"[Bb]eastkin.*[Ww]olf")),
        (CAT, "Cat", re.compile(r"[Cc]at")),
        (CENTAUR, "Centaur", re.compile(r"[Cc]entaur")),
        (CYCLOPS, "Cyclops", re.compile(r"[Cc]yclops")),
        (DEMON, "Demon", re.compile(r"[Dd]emon.*")),
        (DJINNI, "Djinni", re.compile(r"[Dd]jinn[i]?")),
        (DRAGON, "Dragon", re.compile(r"[Dd]ragon.*")),
        (DROWNED_PEOPLE, "Drowned People", re.compile(r"[Dd]rowned")),
        (DRAKE, "Drake", re.compile(r"[Dd]rake")),
        (DULLAHAN, "Dullahan", re.compile(r"[Dd]ullahan")),
        (DRYAD, "Dryad", re.compile(r"[Dd]ryad")),
        (DWARF, "Dwarf", re.compile(r"[Dd]warf")),
        (ELF, "Elf", re.compile(r"^\s*[Ee]lf")),
        (ELEMENTAL, "Elemental", re.compile(r"^\s*[Ee]lemental")),
        (FAE, "Fae", re.compile(r"([Ff]ae|[Ff]airy)")),
        (FRAERLING, "Fraerling", re.compile(r"[Ff]raerling")),
        (GARUDA, "Garuda", re.compile(r"[Gg]aruda")),
        (GAZER, "Gazer", re.compile(r"^\s*[Gg]azer")),
        (GNOLL, "Gnoll", re.compile(r"[Gg]noll")),
        (GIANT, "Giant", re.compile(r"^\s*[Gg]iant")),
        (GOBLIN, "Goblin", re.compile(r"[Gg]oblin")),
        (GOLEM, "Golem", re.compile(r"[Gg]olem")),
        (GOD, "God", re.compile(r"[Gg]od")),
        (GRIFFIN, "Griffin", re.compile(r"[Gg]riffin")),
        (HALFLING, "Halfling", re.compile(r"[Hh]alfling")),
        (HALF_ELF, "Half-Elf", re.compile(r"[Hh]alf[-]?[Ee]lf")),
        (HALF_GAZER, "Half-Gazer", re.compile(r"[Hh]alf[-]?[Gg]azer")),
        (HALF_GIANT, "Half-Giant", re.compile(r"[Hh]alf[-]?[Gg]iant")),
        (HALF_TROLL, "Half-Troll", re.compile(r"[Hh]alf[-]?[Tt]roll")),
        (HARPY, "Harpy", re.compile(r"[Hh]arp(y|ies)")),
        (HUMAN, "Human", re.compile(r"[Hh]uman")),
        (KELPIES, "Kelpies", re.compile(r"[Kk]elp(y|ies)")),
        (KITSUNE, "Kitsune", re.compile(r"[Kk]itsune")),
        (LIVING_ARMOR, "Living Armor", re.compile(r"[Ll]iving [Aa]rmor")),
        (LIZARDFOLK_GORGON, "Lizardfolk - Gorgon", re.compile(r"[Gg]orgon")),
        (LIZARDFOLK_INDISHEI, "Lizardfolk - Indishei", re.compile(r"[Ii]ndishei")),
        (LIZARDFOLK_MEDUSA, "Lizardfolk - Medusa", re.compile(r"[Mm]edusa")),
        (LIZARDFOLK_NAGA, "Lizardfolk - Naga", re.compile(r"[Nn]aga")),
        (LIZARDFOLK_QUEXAL, "Lizardfolk - Quexal", re.compile(r"[Qq]uexal")),
        (LIZARDFOLK_SCYLLA, "Lizardfolk - Scylla", re.compile(r"[Ss]cylla")),
        (LIZARDFOLK_STAR_LAMIA, "Lizardfolk - Star Lamia", re.compile(r"[Ss]tar[\s]*[-]?[Ll]amia")),
        (LIZARDFOLK_LAMIA, "Lizardfolk - Lamia", re.compile(r"[Ll]amia")),
        (LIZARDFOLK_TASGIEL, "Lizardfolk - Tasgiel", re.compile(r"[Tt]asgiel")),
        (LIZARDFOLK, "Lizardfolk", re.compile(r"[Ll]izard[-\s]?([Ff]olk|[Mm]an|[Ww]oman)")),
        (LUCIFEN, "Lucifen", re.compile(r"[Ll]ucifen")),
        (MERFOLK, "Merfolk", re.compile(r"[Mm]er[-]?([Ff]olk|[Mm]an|[Ww]oman)")),
        (MIMIC, "Mimic", re.compile(r"[Mm]imic")),
        (MIND, "Mind", re.compile(r"[Mm]ind")),
        (MINOTAUR, "Minotaur", re.compile(r"[Mm]inotaur")),
        (OGRE, "Ogre", re.compile(r"[Oo]gre")),
        (PEGASIS, "Pegasis", re.compile(r"[Pp]egasis")),
        (PHOENIX, "Phoenix", re.compile(r"[Pp]oenix")),
        (RAT, "Rat", re.compile(r"[Rr]at")),
        (RASKGHAR, "Raskghar", re.compile(r"[Rr]askghar")),
        (REVENANT, "Revenant", re.compile(r"[Rr]evenant")),
        (SARIANT_LAMB, "Sariant Lamb", re.compile(r"[Ss]ariant\s*[-]?[Ll]amb")),
        (SCORCHLING, "Scorchling", re.compile(r"[Ss]corchling")),
        (SEAMWALKER, "Seamwalker", re.compile(r"[Ss]eam[-]?[Ww]alker")),
        (SELPHID, "Selphid", re.compile(r"[Ss]elphid")),
        (SLIME, "Slime", re.compile(r"[Ss]lime")),
        (SPIDERFOLK, "Spiderfolk", re.compile(r"[Ss]pider\s*[-]?[Ff]olk")),
        (STRING_PEOPLE, "String Person", re.compile(r"[Ss](titch|tring)")),
        (TITAN, "Titan", re.compile(r"[Tt]itan")),
        (TROLL, "Troll", re.compile(r"[Tt]roll")),
        (TREANT, "Treant", re.compile(r"[Tt]reant")),
        (UNDEAD, "Undead", re.compile(r"[Uu]ndead")),
        (UNICORN, "Unicorn", re.compile(r"[Uu]nicorn")),
        (VAMPIRE, "Vampire", re.compile(r"[Vv]ampire")),
        (WYVERN, "Wyvern", re.compile(r"[Ww]yvern")),
        (WYRM, "Wyrm", re.compile(r"[Ww]yrm")),
        (UNKNOWN, "Unknown", re.compile(r"")),
    ]
    # fmt: on

    SPECIES = [(x[0], x[1]) for x in SPECIES_DATA]

    # Status short-codes
    ALIVE = "AL"
    DEAD = "DE"

    STATUSES = [
        (ALIVE, "Alive"),
        (DEAD, "Deceased"),
        (UNDEAD, "Undead"),
        (UNKNOWN, "Unknown"),
    ]

    ref_type = models.OneToOneField(RefType, on_delete=models.CASCADE, primary_key=True)
    first_chapter_appearance = models.ForeignKey(
        Chapter, on_delete=models.CASCADE, null=True
    )
    wiki_uri = models.URLField(null=True)
    status = models.CharField(max_length=2, choices=STATUSES, null=True)
    species = models.CharField(max_length=2, choices=SPECIES, null=True)

    @staticmethod
    def parse_status_str(status: str):
        if status is None:
            return Character.UNKNOWN
        status = status.strip()
        if re.match(r"[Aa]live", status):
            return Character.ALIVE
        elif re.match(r"[Uu]ndead", status):
            return Character.UNDEAD
        elif re.match(r"([Dd]ead|[Dd]eceased)", status):
            return Character.DEAD
        elif re.match(r"([Uu]nknown|[Uu]n-?clear)", status):
            return Character.UNKNOWN
        else:
            return Character.UNKNOWN

    @staticmethod
    def parse_species_str(s: str):
        if s is None:
            return Character.UNKNOWN

        for species in Character.SPECIES_DATA:
            if species[2].search(s):
                return species[0]

        return Character.UNKNOWN

    def __str__(self) -> str:
        return f"(Character: {self.ref_type.name}, Status: {self.status}, Species: {self.species})"


class Item(models.Model):
    ref_type = models.OneToOneField(RefType, on_delete=models.CASCADE)
    first_chapter_ref = models.ForeignKey(Chapter, on_delete=models.CASCADE, null=True)
    wiki_uri = models.URLField(null=True)

    def __str__(self) -> str:
        return f"(Item: {self.ref_type.name}, Wiki: {self.wiki_uri})"


class Location(models.Model):
    ref_type = models.OneToOneField(RefType, on_delete=models.CASCADE)
    first_chapter_ref = models.ForeignKey(Chapter, on_delete=models.CASCADE, null=True)
    wiki_uri = models.URLField(null=True)

    def __str__(self) -> str:
        return f"(Location: {self.ref_type.name}, Wiki: {self.wiki_uri})"


class Skill(models.Model):
    ref_type = models.OneToOneField(RefType, on_delete=models.CASCADE)
    first_chapter_ref = models.ForeignKey(Chapter, on_delete=models.CASCADE, null=True)
    wiki_uri = models.URLField(null=True)

    def __str__(self) -> str:
        return f"(Skill: {self.ref_type.name}, Wiki: {self.wiki_uri})"


class Spell(models.Model):
    ref_type = models.OneToOneField(RefType, on_delete=models.CASCADE)
    first_chapter_ref = models.ForeignKey(Chapter, on_delete=models.CASCADE, null=True)
    wiki_uri = models.URLField(null=True)

    def __str__(self) -> str:
        return f"(Spell: {self.ref_type.name}, Wiki: {self.wiki_uri})"


class Alias(models.Model):
    """RefType aliases / alternate names"""

    name = models.TextField()
    ref_type = models.ForeignKey(RefType, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Aliases"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["name", "ref_type"], name="unique_alias")
        ]

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
        ordering = [
            "chapter_line__chapter",
            "chapter_line__line_number",
            "start_column",
        ]
        constraints = [
            models.UniqueConstraint(
                name="textref_key",
                fields=["chapter_line", "start_column", "end_column"],
            )
        ]

    def __str__(self):
        return f"(TextRef: {self.type}, line: {self.chapter_line.line_number:>5}, start: {self.start_column:>4}, end: {self.end_column:>4})"


class RefTypeChapter(models.Model):
    """Chapter references by RefType
    Indexes the chapters in which a RefType has one or more references
    """

    type = models.ForeignKey(RefType, on_delete=models.CASCADE)
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "RefType Chapters"
        constraints = [
            models.UniqueConstraint(
                name="reftype_chapters_key",
                fields=["type", "chapter"],
            )
        ]

    def __str__(self):
        return f"RefTypeChapters: {self.type}, Chapter: {self.chapter.title} - {self.chapter.number:>4}"


class RefTypeComputedView(models.Model):
    """RefType Computed View
    Contains any additional RefType data that requires long running computations, to be materialized as needed
    """

    ref_type = models.OneToOneField(
        RefType, on_delete=models.DO_NOTHING, primary_key=True, db_column="ref_type"
    )
    mentions = models.PositiveIntegerField()
    # first_mention_chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE)

    def delete(self):
        RefTypeComputedView.objects.raw(
            "DELETE FROM reftype_computed_view INNER JOIN stats_reftype as sr ON ref_type = \
                                        sr.id WHERE sr.name = %s AND sr.type = %s",
            params=[self.ref_type.name, self.ref_type.type],
        )

    class Meta:
        managed = False
        db_table = "reftype_computed_view"
