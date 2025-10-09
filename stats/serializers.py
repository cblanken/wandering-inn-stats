from django.contrib.auth import get_user_model
from rest_framework import serializers
from stats.models import Book, Chapter


# Serializers define the API representation.
class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ["url", "username", "email", "is_staff"]


class ChapterSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Chapter
        fields = ["title", "number", "post_date", "word_count"]


class BookSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Book
        fields = ["title", "number"]
