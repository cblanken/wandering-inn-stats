from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Length
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from dataclasses import dataclass
from enum import Enum
import re

models.CharField.register_lookup(Length, "length")


class ColorCategory(models.Model):
    """Model linking Colors to a their corresponding categories"""

    name = models.CharField(max_length=50, unique=True, verbose_name="Color")

    class Meta:
        verbose_name_plural = "Color Categories"

    def __str__(self) -> str:
        return f"(ColorCategory: {self.name})"


class Color(models.Model):
    """Model for colored text"""

    rgb = models.CharField(
        max_length=6,
        validators=[RegexValidator(r"^[a-zA-Z\d]{6}$")],
    )
    category = models.ForeignKey(ColorCategory, on_delete=models.CASCADE, verbose_name="Color Category")

    class Meta:
        ordering = ["rgb"]

    def __str__(self) -> str:
        return f"(Color: {self.category.name}: {self.rgb})"


class Volume(models.Model):
    "Model for volumes"

    number = models.PositiveIntegerField(unique=True, verbose_name="Volume Number")
    title = models.TextField(unique=True, verbose_name="Volume Title")
    summary = models.TextField(default="")

    class Meta:
        ordering = ["number"]

    def __str__(self) -> str:
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
            models.UniqueConstraint(fields=["volume", "title"], name="unique_volume_and_title"),
            models.UniqueConstraint(fields=["volume", "number"], name="unique_volume_and_book_num"),
        ]

    def __str__(self) -> str:
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
    digest = models.CharField(default="")

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
        constraints = [models.CheckConstraint(check=Q(digest__length=64) | Q(digest__length=0), name="digest_length")]

    def __str__(self) -> str:
        return f"(Chapter: {self.title}, URL: {self.source_url})"


class RefType(models.Model):
    """Reference keywords / phrases"""

    class Type(models.TextChoices):
        CHARACTER = "CH", _("Character")
        CLASS = "CL", _("Class")
        CLASS_UPDATE = "CO", _("Class Update")
        CONDITION = "CN", _("Condition Update")
        ITEM = "IT", _("Items and Artifacts")
        LOCATION = "LO", _("Location")
        MIRACLE = "MI", _("Miracle")
        MAGICAL_CHAT = "MC", _("Magical Chat")
        SKILL = "SK", _("Skill")
        SKILL_UPDATE = "SO", _("Skill Update")
        SPELL = "SP", _("Spell")
        SPELL_UPDATE = "SB", _("Spell Update")
        SYSTEM_GENERAL = "SG", _("System General")
        UNDECIDED = "IN", _("Undecided")
        SIGN_LANGUAGE = "SL", _("Sign Language")

    name = models.TextField()
    type = models.CharField(max_length=2, choices=Type.choices, default="")
    slug = models.TextField(default="")
    word_count = models.GeneratedField(  # type: ignore[attr-defined]
        expression=models.Func(
            models.Func(models.F("name"), models.Value(r"\s+"), function="regexp_split_to_array"),
            1,
            function="array_length",
        ),
        output_field=models.IntegerField(),
        db_persist=True,
    )
    letter_count = models.GeneratedField(  # type: ignore[attr-defined]
        expression=models.Func("name", arity=1, function="length", output_field=models.IntegerField()),
        output_field=models.IntegerField(),
        db_persist=True,
    )

    class Meta:
        constraints = [models.UniqueConstraint(fields=["name", "type"], name="unique_name_and_type")]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["type"]),
        ]
        ordering = ["name"]
        verbose_name_plural = "Ref Types"

    def __str__(self) -> str:
        return f"(RefType: {self.name} - Type: {self.type})"

    def save(self, *args, **kwargs) -> None:  # noqa ANN202 ANN203
        self.slug = slugify(self.name[:100], allow_unicode=True)
        super(RefType, self).save(*args, **kwargs)

    def delete(self) -> None:
        computed_cols = RefTypeComputedView.objects.filter(ref_type=self)
        for row in computed_cols:
            row.delete()


@dataclass
class SpeciesMetadata:
    """Class for maintaining Character species shortcodes (enum key), display names, and detection regexes"""

    shortcode: str
    display_name: str
    pattern: re.Pattern


@dataclass
class StatusMetadata:
    """Class for maintaining Character status shortcodes (enum key), display names, and detection regexes"""

    shortcode: str
    display_name: str
    pattern: re.Pattern


class Character(models.Model):
    """Character data"""

    # fmt: off

    # Status short-codes
    class Status(Enum):
        ALIVE = StatusMetadata("AL", "Alive", re.compile(r"[Aa]live"))
        DEAD = StatusMetadata("DE", "Deceased", re.compile(r"([Dd]ead|[Dd]eceased)"))
        UNDEAD = StatusMetadata("UD", "Undead", re.compile(r"[Uu]ndead"))
        UNKNOWN = StatusMetadata("UK", "Unknown", re.compile(r"([Uu]nknown|[Uu]n-?clear)"))

    # Species short-codes
    class Species(Enum):
        AGELUM = SpeciesMetadata("AG", "Agelum", re.compile(r"[Aa]gelum"))
        ANTINIUM = SpeciesMetadata("AN", "Antinium", re.compile(r"[Aa]ntinium"))
        ASHFIRE_BEE = SpeciesMetadata("AB", "Ashfire Bee", re.compile(r"[Aa]shfire[-\s]?[Bb]ee"))
        BEASTKIN = SpeciesMetadata("BK", "Beastkin", re.compile(r"[Bb]eastkin"))
        BEASTKIN_BEAR = SpeciesMetadata("BB", "Beastkin - Bear", re.compile(r"[Bb]eastkin.*[Bb]ear"))
        BEASTKIN_CAT = SpeciesMetadata("BC", "Beastkin - Cat", re.compile(r"[Bb]eastkin.*[Cc]at"))
        BEASTKIN_DOG = SpeciesMetadata("BD", "Beastkin - Dog", re.compile(r"[Bb]eastkin.*[Dd]og"))
        BEASTKIN_FALCON = SpeciesMetadata("BF", "Beastkin - Falcon", re.compile(r"[Bb]eastkin.*[Ff]alcon"))
        BEASTKIN_FOX = SpeciesMetadata("BX", "Beastkin - Fox", re.compile(r"[Bb]eastkin.*[Ff]ox"))
        BEASTKIN_JACKAL = SpeciesMetadata("BJ", "Beastkin - Jackal", re.compile(r"[Bb]eastkin.*[Jj]ackal"))
        BEASTKIN_OWL = SpeciesMetadata("BO", "Beastkin - Owl", re.compile(r"[Bb]eastkin.*[Oo]wl"))
        BEASTKIN_RABBIT = SpeciesMetadata("BR", "Beastkin - Rabbit", re.compile(r"[Bb]eastkin.*[Rr]abbit"))
        BEASTKIN_RHINO = SpeciesMetadata("BH", "Beastkin - Rhino", re.compile(r"[Bb]eastkin.*[Rr]hino.*"))
        BEASTKIN_SALAMANDER = SpeciesMetadata("BS", "Beastkin - Salamander", re.compile(r"[Bb]eastkin.*[Ss]alamander"))
        BEASTKIN_SQUIRREL = SpeciesMetadata("BQ", "Beastkin - Squirrel", re.compile(r"[Bb]eastkin.*[Ss]quirrel"))
        BEASTKIN_WOLF = SpeciesMetadata("BW", "Beastkin - Wolf", re.compile(r"[Bb]eastkin.*[Ww]olf"))
        CAT = SpeciesMetadata("CA", "Cat", re.compile(r"[Cc]at"))
        CENTAUR = SpeciesMetadata("CT", "Centaur", re.compile(r"[Cc]entaur"))
        CYCLOPS = SpeciesMetadata("CY", "Cyclops", re.compile(r"[Cc]yclops"))
        DEMON = SpeciesMetadata("DE", "Demon", re.compile(r"[Dd]emon.*"))
        DJINNI = SpeciesMetadata("DJ", "Djinni", re.compile(r"[Dd]jinn[i]?"))
        DRAGON = SpeciesMetadata("DG", "Dragon", re.compile(r"[Dd]ragon.*"))
        DRAKE = SpeciesMetadata("DR", "Drake", re.compile(r"[Dd]rake"))
        DROWNED_PEOPLE = SpeciesMetadata("DP", "Drowned People", re.compile(r"[Dd]rowned"))
        DRYAD = SpeciesMetadata("DY", "Dryad", re.compile(r"[Dd]ryad"))
        DULLAHAN = SpeciesMetadata("DU", "Dullahan", re.compile(r"[Dd]ullahan"))
        DWARF = SpeciesMetadata("DW", "Dwarf", re.compile(r"[Dd]warf"))
        ELEMENTAL = SpeciesMetadata("EM", "Elemental", re.compile(r"\s*[Ee]lemental"))
        ELF = SpeciesMetadata("EL", "Elf", re.compile(r"^\s*[Ee]lf"))
        FAE = SpeciesMetadata("FA", "Fae", re.compile(r"([Ff]ae|[Ff]airy)"))
        FRAERLING = SpeciesMetadata("FR", "Fraerling", re.compile(r"[Ff]raerling"))
        GARUDA = SpeciesMetadata("GR", "Garuda", re.compile(r"[Gg]aruda"))
        GAZER = SpeciesMetadata("GA", "Gazer", re.compile(r"^\s*[Gg]azer"))
        GIANT = SpeciesMetadata("GI", "Giant", re.compile(r"^\s*[Gg]iant"))
        GNOLL = SpeciesMetadata("GN", "Gnoll", re.compile(r"[Gg]noll"))
        GOBLIN = SpeciesMetadata("GB", "Goblin", re.compile(r"([Gg]oblin|[Ff]omirelin)"))
        GOD = SpeciesMetadata("GO", "God", re.compile(r"[Gg]od"))
        GOLEM = SpeciesMetadata("GM", "Golem", re.compile(r"[Gg]olem"))
        GRIFFIN = SpeciesMetadata("GR", "Griffin", re.compile(r"[Gg]riffin"))
        HALFLING = SpeciesMetadata("HA", "Halfling", re.compile(r"[Hh]alfling"))
        HALF_ELF = SpeciesMetadata("HE", "Half-Elf", re.compile(r"[Hh]alf[-]?[Ee]lf"))
        HALF_GAZER = SpeciesMetadata("HG", "Half-Gazer", re.compile(r"[Hh]alf[-]?[Gg]azer"))
        HALF_GIANT = SpeciesMetadata("HI", "Half-Giant", re.compile(r"[Hh]alf[- ]?[Gg]iant"))
        HALF_TROLL = SpeciesMetadata("HT", "Half-Troll", re.compile(r"[Hh]alf[- ]?[Tt]roll"))
        HARPY = SpeciesMetadata("HR", "Harpy", re.compile(r"[Hh]arp(y|ies)"))
        HUMAN = SpeciesMetadata("HU", "Human", re.compile(r"[Hh]uman"))
        KELPIES = SpeciesMetadata("KE", "Kelpies", re.compile(r"[Kk]elp(y|ies)"))
        KITSUNE = SpeciesMetadata("KI", "Kitsune", re.compile(r"[Kk]itsune"))
        LIVING_ARMOR = SpeciesMetadata("LA", "Living Armor", re.compile(r"[Ll]iving [Aa]rmor"))
        LIZARDFOLK = SpeciesMetadata("LF", "Lizardfolk", re.compile(r"[Ll]izard[-\s]?([Ff]olk|[Mm]an|[Ww]oman)"))
        LIZARDFOLK_GORGON = SpeciesMetadata("LG", "Lizardfolk - Gorgon", re.compile(r"[Gg]orgon"))
        LIZARDFOLK_INDISHEI = SpeciesMetadata("LI", "Lizardfolk - Indishei", re.compile(r"[Ii]ndishei"))
        LIZARDFOLK_LAMIA = SpeciesMetadata("LL", "Lizardfolk - Lamia", re.compile(r"[Ll]amia"))
        LIZARDFOLK_MEDUSA = SpeciesMetadata("LM", "Lizardfolk - Medusa", re.compile(r"[Mm]edusa"))
        LIZARDFOLK_NAGA = SpeciesMetadata("LN", "Lizardfolk - Naga", re.compile(r"[Nn]aga"))
        LIZARDFOLK_QUEXAL = SpeciesMetadata("LQ", "Lizardfolk - Quexal", re.compile(r"[Qq]uexal"))
        LIZARDFOLK_SCYLLA = SpeciesMetadata("LS", "Lizardfolk - Scylla", re.compile(r"[Ss]cylla"))
        LIZARDFOLK_STAR_LAMIA = SpeciesMetadata("LR", "Lizardfolk - Star Lamia", re.compile(r"[Ss]tar[\s]*[-]?[Ll]amia"))
        LIZARDFOLK_TASGIEL = SpeciesMetadata("LT", "Lizardfolk - Tasgiel", re.compile(r"[Tt]asgiel"))
        LUCIFEN = SpeciesMetadata("LU", "Lucifen", re.compile(r"[Ll]ucifen"))
        MERFOLK = SpeciesMetadata("ME", "Merfolk", re.compile(r"[Mm]er[-]?([Ff]olk|[Mm]an|[Ww]oman)"))
        MIMIC = SpeciesMetadata("MM", "Mimic", re.compile(r"[Mm]imic"))
        MIND = SpeciesMetadata("MN", "Mind", re.compile(r"[Mm]ind"))
        MINOTAUR = SpeciesMetadata("MI", "Minotaur", re.compile(r"[Mm]inotaur"))
        OGRE = SpeciesMetadata("OG", "Ogre", re.compile(r"[Oo]gre"))
        PEGASIS = SpeciesMetadata("PG", "Pegasis", re.compile(r"[Pp]egasis"))
        PHOENIX = SpeciesMetadata("PH", "Phoenix", re.compile(r"[Pp]oenix"))
        RASKGHAR = SpeciesMetadata("RG", "Raskghar", re.compile(r"[Rr]askghar"))
        RAT = SpeciesMetadata("RA", "Rat", re.compile(r"[Rr]at"))
        REVENANT = SpeciesMetadata("RE", "Revenant", re.compile(r"[Rr]evenant"))
        SARIANT_LAMB = SpeciesMetadata("SL", "Sariant Lamb", re.compile(r"[Ss]ariant\s*[-]?[Ll]amb"))
        SCORCHLING = SpeciesMetadata("SH", "Scorchling", re.compile(r"[Ss]corchling"))
        SEAMWALKER = SpeciesMetadata("SW", "Seamwalker", re.compile(r"[Ss]eam[-]?[Ww]alker"))
        SELPHID = SpeciesMetadata("SE", "Selphid", re.compile(r"[Ss]elphid"))
        SLIME = SpeciesMetadata("SL", "Slime", re.compile(r"[Ss]lime"))
        SPIDERFOLK = SpeciesMetadata("SF", "Spiderfolk", re.compile(r"[Ss]pider\s*[-]?[Ff]olk"))
        STRING_PEOPLE = SpeciesMetadata("SP", "String Person", re.compile(r"[Ss](titch|tring)"))
        TITAN = SpeciesMetadata("TI", "Titan", re.compile(r"[Tt]itan"))
        TREANT = SpeciesMetadata("TR", "Treant", re.compile(r"[Tt]reant"))
        TROLL = SpeciesMetadata("TL", "Troll", re.compile(r"[Tt]roll"))
        UNDEAD = SpeciesMetadata("UD", "Undead", re.compile(r"[Uu]ndead"))
        UNICORN = SpeciesMetadata("UC", "Unicorn", re.compile(r"[Uu]nicorn"))
        UNKNOWN = SpeciesMetadata("UK", "Unknown", re.compile(r"^$"))
        VAMPIRE = SpeciesMetadata("VA", "Vampire", re.compile(r"[Vv]ampire"))
        WYRM = SpeciesMetadata("WY", "Wyrm", re.compile(r"[Ww]yrm"))
        WYVERN = SpeciesMetadata("WV", "Wyvern", re.compile(r"[Ww]yvern"))
    # fmt: on

    STATUSES = [(s.value.shortcode, s.value.display_name) for s in Status]
    SPECIES = [(s.value.shortcode, s.value.display_name) for s in Species]

    ref_type = models.OneToOneField(RefType, on_delete=models.CASCADE, primary_key=True)
    first_chapter_appearance = models.ForeignKey(Chapter, on_delete=models.CASCADE, null=True)
    wiki_uri = models.URLField(default="")
    status = models.CharField(max_length=2, choices=STATUSES, default="")
    species = models.CharField(max_length=2, choices=SPECIES, default="")

    def __str__(self) -> str:
        return f"(Character: {self.ref_type.name}, Status: {self.status}, Species: {self.species})"

    @staticmethod
    def identify_status(s: str | None) -> str:
        """Identifies the status of the input string and returns the corresponding shortcode"""
        if s is None:
            return Character.Status.UNKNOWN.value.shortcode

        for status in Character.Status:
            if status.value.pattern.match(s):
                return status.value.shortcode

        return Character.Status.UNKNOWN.value.shortcode

    @staticmethod
    def identify_species(s: str | None) -> str:
        """Identifies the species of the input string and returns the corresponding shortcode"""
        if s is None:
            return Character.Species.UNKNOWN.value.shortcode

        for species in Character.Species:
            if species.value.pattern.search(s):
                return species.value.shortcode

        return Character.Species.UNKNOWN.value.shortcode


class Item(models.Model):
    ref_type = models.OneToOneField(RefType, on_delete=models.CASCADE)
    first_chapter_ref = models.ForeignKey(Chapter, on_delete=models.CASCADE, null=True)
    wiki_uri = models.URLField(default="")

    def __str__(self) -> str:
        return f"(Item: {self.ref_type.name}, Wiki: {self.wiki_uri})"


class Location(models.Model):
    ref_type = models.OneToOneField(RefType, on_delete=models.CASCADE)
    first_chapter_ref = models.ForeignKey(Chapter, on_delete=models.CASCADE, null=True)
    wiki_uri = models.URLField(default="")

    def __str__(self) -> str:
        return f"(Location: {self.ref_type.name}, Wiki: {self.wiki_uri})"


class Skill(models.Model):
    ref_type = models.OneToOneField(RefType, on_delete=models.CASCADE)
    first_chapter_ref = models.ForeignKey(Chapter, on_delete=models.CASCADE, null=True)
    wiki_uri = models.URLField(default="")

    def __str__(self) -> str:
        return f"(Skill: {self.ref_type.name}, Wiki: {self.wiki_uri})"


class Spell(models.Model):
    ref_type = models.OneToOneField(RefType, on_delete=models.CASCADE)
    first_chapter_ref = models.ForeignKey(Chapter, on_delete=models.CASCADE, null=True)
    wiki_uri = models.URLField(default="")

    def __str__(self) -> str:
        return f"(Spell: {self.ref_type.name}, Wiki: {self.wiki_uri})"


class Alias(models.Model):
    """RefType aliases / alternate names"""

    name = models.TextField()
    ref_type = models.ForeignKey(RefType, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Aliases"
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["name", "ref_type"], name="unique_alias")]

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
        constraints = [models.UniqueConstraint(fields=["chapter", "line_number"], name="unique_chapter_and_line")]

    def __str__(self) -> str:
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
            ),
        ]

    def __str__(self) -> str:
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
            ),
        ]

    def __str__(self) -> str:
        return f"RefTypeChapters: {self.type}, Chapter: {self.chapter.title} - {self.chapter.number:>4}"


class RefTypeComputedView(models.Model):
    """RefType Computed View
    Contains any additional RefType data that requires long running computations, to be materialized as needed
    """

    ref_type = models.OneToOneField(RefType, on_delete=models.DO_NOTHING, primary_key=True, db_column="ref_type")
    mentions = models.PositiveIntegerField()
    # first_mention_chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE)

    class Meta:
        managed = False
        db_table = "reftype_computed_view"

    def __str__(self) -> str:
        return f"RefTypeComputed: {self.ref_type}, Mentions: {self.mentions}"

    def delete(self) -> None:
        RefTypeComputedView.objects.raw(
            "DELETE FROM reftype_computed_view INNER JOIN stats_reftype as sr ON ref_type = \
                                        sr.id WHERE sr.name = %s AND sr.type = %s",
            params=[self.ref_type.name, self.ref_type.type],
        )
