from rest_framework import serializers

from apps.catalog.models import Category
from apps.invoices.models import Invoice
from apps.invoices.serializers import InvoiceSerializer

from .models import Order


class OrderFullSerializer(serializers.ModelSerializer):
    """Admin / AccountsFull / the order's own customer: full financial detail."""

    category = serializers.SlugRelatedField(
        slug_field="slug", queryset=Category.objects.all(), required=False, allow_null=True
    )
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    product_name = serializers.CharField(source="product.name", read_only=True, default=None)
    fabric_name = serializers.CharField(source="fabric.name", read_only=True, default=None)
    design_code = serializers.CharField(source="design.code", read_only=True, default=None)
    due_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    invoice = serializers.SerializerMethodField()

    def get_invoice(self, obj):
        try:
            return InvoiceSerializer(obj.invoice).data
        except Invoice.DoesNotExist:
            return None

    class Meta:
        model = Order
        fields = [
            "id",
            "reference_code",
            "quote_request",
            "customer",
            "name",
            "phone",
            "email",
            "category",
            "category_name",
            "product",
            "product_name",
            "fabric",
            "fabric_name",
            "design",
            "design_code",
            "total_quantity",
            "size_breakdown",
            "unit_price",
            "total_value",
            "advance_paid",
            "due_amount",
            "status",
            "admin_notes",
            "invoice",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "reference_code", "created_by", "created_at", "updated_at"]


class OrderLimitedSerializer(serializers.ModelSerializer):
    """AccountsLimited: operational detail only -- no pricing/payment fields.
    For staff (e.g. production/warehouse) who need to fulfil an order without
    seeing what the customer is being charged."""

    category = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    product_name = serializers.CharField(source="product.name", read_only=True, default=None)
    fabric_name = serializers.CharField(source="fabric.name", read_only=True, default=None)
    design_code = serializers.CharField(source="design.code", read_only=True, default=None)

    class Meta:
        model = Order
        fields = [
            "id",
            "reference_code",
            "name",
            "phone",
            "category",
            "category_name",
            "product",
            "product_name",
            "fabric",
            "fabric_name",
            "design",
            "design_code",
            "total_quantity",
            "size_breakdown",
            "status",
            "created_at",
        ]
        read_only_fields = fields
