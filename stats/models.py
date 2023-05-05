from django.db import models

class ColorCategory(models.Model):
    """Model linking Colors to a their corresponding categories"""
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return f"ColorCategory: {self.name}"

class Color(models.Model):
    """Model for colored text"""
    #TODO: add rgb regex constraint
    rgb = models.CharField()
    color = models.ForeignKey(ColorCategory, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.color.name}: {self.rgb}"


class LevelingToken(models.Model):
    """Model for all Leveling System tokens including [Classes], [Skills], [Spells],
    and [Miracles]
    """
    TOKEN_TYPES = [
        ("cl", "Class"),
        ("sk", "Skill"),
        ("sp", "Spell"),
        ("mi", "Miracle"),
        ("ob", "Something Obtained"),
    ]

    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=500)
    faith_based = models.BooleanField(default=False)
    color = models.ForeignKey(Color, on_delete=models.CASCADE)
    type = models.CharField(max_length=2, choices=TOKEN_TYPES)

    def __str__(self):
        return f"{self.name}: {self.type}"

class Character(models.Model):
    """Model for characters"""
    name = models.CharField(max_length=50)
    alt_names = models.JSONField

    def __str__(self):
        return f"{self.name}: {self.alt_names}"

class Volume(models.Model):
    "Model for volumes"
    number = models.PositiveIntegerField(unique=True)
    title = models.CharField(max_length=50, unique=True)
    summary = models.TextField(default="")

    def __str__(self):
        return f"Volume: {self.title}, Summary: {str(self.summary)[:30]}..."

class Book(models.Model):
    "Mode for books"
    number = models.PositiveBigIntegerField()
    title = models.CharField(max_length=50, unique=True)
    summary = models.TextField(default="")
    volume = models.ForeignKey(Volume, on_delete=models.CASCADE)

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

    def __str__(self) -> str:
        return f"Chapter: {self.title}, URL: {self.source_url}"

class TextRef(models.Model):
    """Model for text references to keywords"""
    text = models.TextField()
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE)
    line_number = models.PositiveIntegerField()
    start_column = models.PositiveIntegerField()
    end_column = models.PositiveIntegerField()
    context_offset = models.PositiveBigIntegerField(default=50)

    def __str__(self):
        return f"{self.line_number:>5}{self.start_column:>4}{self.end_column:>4}"