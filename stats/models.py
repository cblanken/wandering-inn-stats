from django.db import models

class Color(models.Model):
    """Model for colored text"""
    name = models.CharField(max_length=50, unique=True)
    rgb = models.CharField()
    #TODO: add rgb regex constraint

    def __str__(self):
        return f"{self.name}: {self.rgb}"

class LevelingToken(models.Model):
    """Model for all Leveling System tokens including [Classes], [Skills], [Spells],
    and [Miracles]"""
    TOKEN_TYPES = [
        ("CL", "Class"),
        ("SK", "Skill"),
        ("SP", "Spell"),
        ("MR", "Miracle")
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

class Volume(models.Model):
    "Model for book volumes"
    number = models.PositiveIntegerField(unique=True)
    title = models.CharField(max_length=50, unique=True)
    summary = models.TextField()

class Chapter(models.Model):
    "Model for book chapters"
    title = models.CharField(max_length=50)
    text = models.TextField(unique=True, default="")
    is_interlude = models.BooleanField()
    source_url = models.URLField(unique=True)
    post_date = models.DateField()
    volume = models.ForeignKey(Volume, on_delete=models.CASCADE)

class TextRef(models.Model):
    """Model for text references to keywords"""
    text = models.TextField()
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE)
    line_number = models.PositiveIntegerField()
    start_column = models.PositiveIntegerField()
    end_column = models.PositiveIntegerField()
    context_offset = models.PositiveBigIntegerField(default=50)