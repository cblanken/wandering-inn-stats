"""API views"""

from django.contrib.auth import get_user_model
from rest_framework import permissions as perms, viewsets
from stats.models import Chapter
from stats.serializers import UserSerializer, ChapterSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = get_user_model().objects.all()
    serializer_class = UserSerializer
    permission_classes = [perms.IsAuthenticated, perms.IsAdminUser]


class ChapterViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Chapter.objects.all()
    serializer_class = ChapterSerializer
    http_method_names = ["get"]
    permission_classes = [perms.IsAuthenticatedOrReadOnly]


class LongestChaptersViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Chapter.objects.filter(is_canon=True).order_by("-word_count")[:5]
    serializer_class = ChapterSerializer
    http_method_names = ["get"]
    permission_classes = [perms.IsAuthenticatedOrReadOnly]
