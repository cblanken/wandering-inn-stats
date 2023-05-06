from django.db import models

class ColorCategory(models.Model):
    """Model linking Colors to a their corresponding categories"""
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name_plural = "Color Categories"

    def __str__(self):
        return f"ColorCategory: {self.name}"

class Color(models.Model):
    """Model for colored text"""
    #TODO: add rgb regex constraint
    rgb = models.CharField()
    category = models.ForeignKey(ColorCategory, on_delete=models.CASCADE)

    class Meta:
        ordering = ["rgb"]

    def __str__(self):
        return f"Color: {self.category.name}: {self.rgb}"

class Volume(models.Model):
    "Model for volumes"
    number = models.PositiveIntegerField(unique=True)
    title = models.CharField(max_length=50, unique=True)
    summary = models.TextField(default="")

    class Meta:
        ordering = ["number"]

    def __str__(self):
        return f"Volume: {self.title}, Summary: {str(self.summary)[:30]}..."

class Book(models.Model):
    "Mode for books"
    number = models.PositiveBigIntegerField()
    title = models.CharField(max_length=50, unique=True)
    summary = models.TextField(default="")
    volume = models.ForeignKey(Volume, on_delete=models.CASCADE)

    class Meta:
        ordering = ["volume", "number"]

    def __str__(self):
        return f"Book: {self.title}, Summary: {str(self.summary)[:30]}"

class Chapter(models.Model):
    "Model for book chapters"
    number = models.PositiveBigIntegerField()
    title = models.CharField(max_length=50)
    is_interlude = models.BooleanField()
    source_url = models.URLField()
    post_date = models.DateField(auto_now=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)

    class Meta:
        ordering = ["book", "number"]

    def __str__(self) -> str:
        return f"Chapter: {self.title}, URL: {self.source_url}"

class RefType(models.Model):
    """Reference keywords / phrases"""
    CLASS = "CL"
    CLASS_OBTAINED = "CO"
    SKILL = "SK"
    SKILL_OBTAINED = "SO"
    SPELL = "SP"
    SPELL_OBTAINED = "SB"
    CHARACTER = "CH"
    ITEM = "IT"
    LOCATION = "LO"
    TYPES = [
        (CLASS, "Class"),
        (CLASS_OBTAINED, "Class Obtained"),
        (SKILL, "Skill"),
        (SKILL_OBTAINED, "Skill Obtained"),
        (SPELL, "Spell"),
        (SPELL_OBTAINED, "Spell Obtained"),
        (CHARACTER, "Character"),
        (ITEM, "Item"),
        (LOCATION, "Location"),
    ]
    name = models.CharField(max_length=120, unique=True)
    type = models.CharField(max_length=2, choices=TYPES, null=True)
    description = models.CharField(max_length=120, default="")
    is_divine = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Ref Types"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} - Type: {self.type}, is_divine: {self.is_divine}"

class Alias(models.Model):
    """RefType aliases / alternate names"""
    name = models.CharField(unique=True)
    ref_type = models.ForeignKey(RefType, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Aliases"

    def __str__(self) -> str:
        return f"Alias: {self.name} - RefType: {self.ref_type}"

class TextRef(models.Model):
    """Instances of Ref(s) found in text"""
    text = models.TextField()
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE)
    type = models.ForeignKey(RefType, on_delete=models.CASCADE)
    line_number = models.PositiveIntegerField()
    start_column = models.PositiveIntegerField()
    end_column = models.PositiveIntegerField()
    context_offset = models.PositiveBigIntegerField(default=50)

    class Meta:
        verbose_name_plural = "Text Refs"

    def __str__(self):
        return f"{self.text} - type: {self.type}, line: {self.line_number:>5}, start: {self.start_column:>4}, end: {self.end_column:>4}"