import io
import os
from datetime import timedelta
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.catalog.models import Category, CategoryFilterOption, Design, Fabric, Product
from apps.invoices.models import Invoice
from apps.invoices.services import generate_and_send_invoice
from apps.orders.models import Order, OrderStatus
from apps.pricing.services import estimate_price
from apps.quotes.models import QuoteRequest, QuoteRequestStatus
from apps.reviews.models import Review, ReviewStatus
from apps.users.models import StaffInvite, User
from apps.wishlist.models import WishlistItem

DEV_PASSWORD = "Str0ngPassw0rd!"

# Fake by default (never committed real inboxes to source) -- since real SMTP
# sends now bounce silently against @advergo.local, set DEV_ADMIN_EMAIL in
# your own untracked .env to a real address you can check if you want to
# actually receive 2FA codes / reset links while testing locally.
ADMIN_EMAIL = os.environ.get("DEV_ADMIN_EMAIL", "admin@advergo.local")

DESIGN_CATEGORIES = ["polo", "round-neck", "v-neck", "winter-collection"]

CUSTOMERS = [
    {"email": "rafiqul.islam@example.com", "full_name": "Rafiqul Islam", "phone": "+8801711000001"},
    {
        "email": "tanvir.hossain@example.com",
        "full_name": "Tanvir Hossain",
        "phone": "+8801711000002",
    },
    {"email": "sabbir.rahman@example.com", "full_name": "Sabbir Rahman", "phone": None},
    {"email": None, "full_name": "Phone Only Customer", "phone": "+8801711000004"},
]


def _placeholder_image(text: str, color: tuple[int, int, int]) -> ContentFile:
    """Small solid-color PNG with a text label -- good enough to eyeball in the
    admin/API without needing real photography for local exploration."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (600, 600), color=color)
    draw = ImageDraw.Draw(img)
    draw.text((20, 280), text, fill=(255, 255, 255))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return ContentFile(buffer.getvalue(), name=f"{text.lower().replace(' ', '-')}.png")


CATEGORY_COLORS = {
    "polo": (29, 78, 216),
    "round-neck": (5, 150, 105),
    "v-neck": (124, 58, 237),
    "winter-collection": (146, 64, 14),
}


class Command(BaseCommand):
    help = (
        "Populates every app with throwaway dummy data for local exploration: users of every "
        "role, designs, quotes, orders (every status), an invoice, reviews (every status), "
        "wishlist entries, a staff invite. Safe to re-run. Not for staging/production."
    )

    def handle(self, *args, **options):
        self.stdout.write("Running seed_demo_data first (categories/fabrics/products/...)")
        call_command("seed_demo_data")

        self._seed_users()
        self._seed_designs()
        self._seed_reviews()
        self._seed_wishlist()
        quote = self._seed_quote_requests()
        order = self._seed_orders(quote)
        self._seed_invoice(order)
        self._seed_staff_invite()

        self.stdout.write(
            self.style.SUCCESS("\nDev data seeded. Login password for everyone below:")
        )
        self.stdout.write(self.style.SUCCESS(f"  {DEV_PASSWORD}"))
        self.stdout.write(
            "\nAccounts:\n"
            f"  superuser        {ADMIN_EMAIL}\n"
            "  staff (full)     accounts.full@advergo.local\n"
            "  staff (limited)  accounts.limited@advergo.local\n"
            "  customers        rafiqul.islam@example.com, tanvir.hossain@example.com, "
            "sabbir.rahman@example.com, +8801711000004 (phone-only, no email)\n"
            "\nStaff logins require the email-OTP 2FA step -- codes print to the console "
            "(EMAIL_BACKEND=console)."
        )

    def _seed_users(self):
        admin, created = User.objects.get_or_create(
            email=ADMIN_EMAIL,
            defaults={"full_name": "Advergo Admin", "is_staff": True, "is_superuser": True},
        )
        if created:
            admin.set_password(DEV_PASSWORD)
            admin.save(update_fields=["password"])

        from django.contrib.auth.models import Group

        full_group = Group.objects.get(name="AccountsFull")
        limited_group = Group.objects.get(name="AccountsLimited")

        full_staff, created = User.objects.get_or_create(
            email="accounts.full@advergo.local",
            defaults={"full_name": "Accounts Full", "is_staff": True},
        )
        if created:
            full_staff.set_password(DEV_PASSWORD)
            full_staff.save(update_fields=["password"])
        full_staff.groups.add(full_group)

        limited_staff, created = User.objects.get_or_create(
            email="accounts.limited@advergo.local",
            defaults={"full_name": "Accounts Limited", "is_staff": True},
        )
        if created:
            limited_staff.set_password(DEV_PASSWORD)
            limited_staff.save(update_fields=["password"])
        limited_staff.groups.add(limited_group)

        customer_count = 0
        for row in CUSTOMERS:
            lookup = {"email": row["email"]} if row["email"] else {"phone": row["phone"]}
            user, created = User.objects.get_or_create(
                **lookup,
                defaults={
                    "email": row["email"],
                    "phone": row["phone"],
                    "full_name": row["full_name"],
                },
            )
            if created:
                user.set_password(DEV_PASSWORD)
                user.save(update_fields=["password"])
            customer_count += 1

        self.stdout.write(f"  users: 1 superuser, 2 staff, {customer_count} customers")

    def _seed_designs(self):
        count = 0
        for slug in DESIGN_CATEGORIES:
            category = Category.objects.get(slug=slug)
            options = list(CategoryFilterOption.objects.filter(category=category))
            for i in range(6):
                option = options[i % len(options)] if options else None
                label = f"{category.name} Design {i + 1}"
                if Design.objects.filter(
                    category=category, code=f"{slug.upper()}-{i + 1:03d}"
                ).exists():
                    continue
                Design.objects.create(
                    category=category,
                    filter_option=option,
                    name=label,
                    code=f"{slug.upper()}-{i + 1:03d}",
                    image=_placeholder_image(label, CATEGORY_COLORS[slug]),
                    is_active=True,
                    order=i,
                )
                count += 1
        self.stdout.write(f"  designs: {count} created (+ existing)")

    def _seed_reviews(self):
        rows = [
            {
                "name": "Imran Kabir",
                "rating": 3,
                "status": ReviewStatus.PENDING,
                "text": "Decent quality but delivery took longer than quoted.",
            },
            {
                "name": "Nusrat Jahan",
                "rating": 2,
                "status": ReviewStatus.REJECTED,
                "text": "Sizing was off for half the team.",
            },
        ]
        for row in rows:
            Review.objects.get_or_create(name=row["name"], defaults=row)
        self.stdout.write(f"  reviews: {len(rows)} extra (pending/rejected) + existing approved")

    def _seed_wishlist(self):
        customer = User.objects.get(email="rafiqul.islam@example.com")
        products = list(Product.objects.all()[:3])
        count = 0
        for product in products:
            _, created = WishlistItem.objects.get_or_create(user=customer, product=product)
            count += created
        self.stdout.write(f"  wishlist items: {count} created (+ existing)")

    def _seed_quote_requests(self):
        category = Category.objects.get(slug="football")
        fabric = Fabric.objects.first()
        customer = User.objects.get(email="tanvir.hossain@example.com")

        estimate = estimate_price(fabric=fabric, category=category, quantity=30)
        quote, _ = QuoteRequest.objects.get_or_create(
            reference_code="QR-DEV00001",
            defaults={
                "user": customer,
                "name": customer.full_name,
                "phone": customer.phone or "+8801711000002",
                "email": customer.email,
                "category": category,
                "fabric": fabric,
                "quantity": 30,
                "size_breakdown": "6xS, 12xM, 10xL, 2xXL",
                "notes": "Need these before the season opener in 3 weeks.",
                "estimated_price_low": estimate.unit_price_low * 30,
                "estimated_price_high": estimate.unit_price_high * 30,
                "status": QuoteRequestStatus.REVIEWED,
            },
        )
        self.stdout.write("  quote requests: 1 (+ existing)")
        return quote

    def _seed_orders(self, quote):
        category = Category.objects.get(slug="football")
        fabric = Fabric.objects.first()
        product = Product.objects.filter(category=category).first()
        staff = User.objects.get(email="accounts.full@advergo.local")

        statuses = [
            (OrderStatus.CONFIRMED, "ORD-DEV0001"),
            (OrderStatus.IN_PRODUCTION, "ORD-DEV0002"),
            (OrderStatus.QUALITY_CHECK, "ORD-DEV0003"),
            (OrderStatus.READY, "ORD-DEV0004"),
            (OrderStatus.DELIVERED, "ORD-DEV0005"),
            (OrderStatus.CANCELLED, "ORD-DEV0006"),
        ]
        primary_order = None
        for status, ref in statuses:
            order, _ = Order.objects.get_or_create(
                reference_code=ref,
                defaults={
                    "quote_request": quote if ref == "ORD-DEV0001" else None,
                    "customer": quote.user,
                    "name": quote.name,
                    "phone": quote.phone,
                    "email": quote.email,
                    "category": category,
                    "product": product,
                    "fabric": fabric,
                    "total_quantity": 30,
                    "size_breakdown": quote.size_breakdown,
                    "unit_price": Decimal("480.00"),
                    "total_value": Decimal("14400.00"),
                    "advance_paid": Decimal("5000.00"),
                    "status": status,
                    "created_by": staff,
                },
            )
            if ref == "ORD-DEV0001":
                primary_order = order

        self.stdout.write(f"  orders: {len(statuses)} (+ existing), one per status")
        return primary_order

    def _seed_invoice(self, order):
        if order is None or Invoice.objects.filter(order=order).exists():
            self.stdout.write("  invoice: already exists, skipped")
            return
        try:
            generate_and_send_invoice(order)
            self.stdout.write("  invoice: 1 generated (PDF rendered, email printed to console)")
        except Exception as e:  # noqa: BLE001 -- best-effort for local exploration only
            self.stdout.write(self.style.WARNING(f"  invoice: skipped ({e})"))

    def _seed_staff_invite(self):
        from django.contrib.auth.models import Group

        limited_group = Group.objects.get(name="AccountsLimited")
        admin = User.objects.get(email=ADMIN_EMAIL)
        StaffInvite.objects.get_or_create(
            email="pending.invite@example.com",
            defaults={
                "group": limited_group,
                "invited_by": admin,
                "token": "dev-preview-token-not-secure",
                "expires_at": timezone.now() + timedelta(days=7),
            },
        )
        self.stdout.write("  staff invite: 1 pending (+ existing)")
