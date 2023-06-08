from django.contrib import admin
from .models import *

# Organizational data
admin.site.register(Chapter)
admin.site.register(Book)
admin.site.register(Volume)

# Text reference data
admin.site.register(Alias)
admin.site.register(Character)
admin.site.register(Color)
admin.site.register(ColorCategory)
admin.site.register(RefType)
admin.site.register(TextRef)
