import django_filters

from .models import GalleryItem


class GalleryItemFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name="category__slug", lookup_expr="iexact")

    class Meta:
        model = GalleryItem
        fields = ["category"]
