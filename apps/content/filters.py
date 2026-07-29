import django_filters

from .models import GalleryItem


class GalleryItemFilter(django_filters.FilterSet):
    class Meta:
        model = GalleryItem
        fields = ["category"]
