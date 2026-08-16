import django_filters

from .models import Design, Product, SizeChartRow


class ProductFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name="category__slug", lookup_expr="iexact")
    featured = django_filters.BooleanFilter(field_name="is_featured")

    class Meta:
        model = Product
        fields = ["category", "featured"]


class DesignFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name="category__slug", lookup_expr="iexact")
    filter_value = django_filters.CharFilter(
        field_name="filter_option__value", lookup_expr="iexact"
    )

    class Meta:
        model = Design
        fields = ["category", "filter_value"]


class SizeChartRowFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name="category__slug", lookup_expr="iexact")

    class Meta:
        model = SizeChartRow
        fields = ["category"]
