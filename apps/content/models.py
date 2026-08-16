import uuid

from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.core.storage import get_raw_file_storage


class BannerQuerySet(models.QuerySet):
    def active(self):
        now = timezone.now()
        return (
            self.filter(is_active=True)
            .filter(models.Q(featured_from__isnull=True) | models.Q(featured_from__lte=now))
            .filter(models.Q(featured_to__isnull=True) | models.Q(featured_to__gte=now))
            .order_by("-priority", "-created_at")
        )


class Banner(TimeStampedModel):
    """Homepage hero content. `featured_from`/`featured_to` give the
    seasonal-highlight control from the spec (e.g. a winter promo banner
    that's only live for a date range) without needing code changes."""

    title = models.CharField(
        max_length=150,
        help_text="Use a line break to control where the red accent line starts, e.g. "
        "'Built for champions.\\nMade your way.' -- the part after the break is highlighted red.",
    )
    subtitle = models.CharField(max_length=300, blank=True)
    image = models.ImageField(upload_to="advergo/banners/", blank=True, null=True)
    cta_label = models.CharField(max_length=40, blank=True)
    cta_href = models.CharField(max_length=200, blank=True)

    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(
        default=0, help_text="Higher priority wins when multiple banners are active."
    )
    featured_from = models.DateTimeField(null=True, blank=True)
    featured_to = models.DateTimeField(null=True, blank=True)

    objects = BannerQuerySet.as_manager()

    class Meta:
        ordering = ["-priority", "-created_at"]

    def __str__(self):
        return self.title


class Stat(TimeStampedModel):
    value = models.CharField(max_length=30)
    label = models.CharField(max_length=80)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.value} {self.label}"


class AchievementKind(models.TextChoices):
    DOCUMENT = "document", "Legal document"
    AWARD = "award", "Award"


class Achievement(TimeStampedModel):
    kind = models.CharField(max_length=10, choices=AchievementKind.choices)
    image = models.ImageField(upload_to="advergo/achievements/", blank=True, null=True)
    title = models.CharField(max_length=120)
    year = models.CharField(max_length=10, blank=True)
    issuing_body = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title


class ClientLogo(TimeStampedModel):
    name = models.CharField(max_length=120)
    # Either an external URL (e.g. Clearbit's logo API) or an uploaded image --
    # logo_image wins when both are set (see `logo` property).
    logo_url = models.URLField(blank=True)
    logo_image = models.ImageField(upload_to="advergo/clients/", blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    @property
    def logo(self):
        return self.logo_image.url if self.logo_image else self.logo_url


class ProcessStep(TimeStampedModel):
    number = models.CharField(max_length=4)
    title = models.CharField(max_length=120)
    description = models.TextField()
    emoji = models.CharField(max_length=8, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.number} · {self.title}"


class GalleryCategory(TimeStampedModel):
    """Gallery photo category (factory, clients, ...), kept as data, not an
    enum, so new categories can be added from the admin without a deploy."""

    slug = models.SlugField(unique=True, max_length=40)
    name = models.CharField(max_length=80)
    icon = models.CharField(max_length=8, blank=True, help_text="Emoji shown in the UI.")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "gallery categories"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class GalleryItem(TimeStampedModel):
    image = models.ImageField(upload_to="advergo/gallery/", blank=True, null=True)
    label = models.CharField(max_length=120)
    category = models.ForeignKey(
        GalleryCategory, on_delete=models.PROTECT, related_name="gallery_items"
    )
    description = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "-created_at"]

    def __str__(self):
        return self.label


class CompanyInfo(TimeStampedModel):
    """Singleton -- always exactly one row, fixed at SINGLETON_ID."""

    SINGLETON_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

    name = models.CharField(max_length=150)
    tagline = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    email_alt = models.EmailField(blank=True)
    website = models.CharField(max_length=150, blank=True)
    head_office = models.CharField(max_length=250, blank=True)
    factory = models.CharField(max_length=250, blank=True)
    founded = models.CharField(max_length=10, blank=True)
    md = models.CharField(max_length=120, blank=True)
    chairman = models.CharField(max_length=120, blank=True)
    trade_license_no = models.CharField(max_length=60, blank=True)
    about = models.TextField(blank=True)
    mission = models.TextField(blank=True)
    vision = models.TextField(blank=True)

    class Meta:
        verbose_name = verbose_name_plural = "company info"

    def save(self, *args, **kwargs):
        self.pk = self.SINGLETON_ID
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # singleton: never actually deletable from the admin

    def __str__(self):
        return self.name


class TeamMember(TimeStampedModel):
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=120)
    photo = models.ImageField(upload_to="advergo/team/", blank=True, null=True)
    bio = models.TextField(blank=True, help_text="Leadership quote/bio; usually blank for staff.")
    is_leadership = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.name} ({self.role})"


class BankAccount(TimeStampedModel):
    bank_name = models.CharField(max_length=120)
    account_name = models.CharField(max_length=150)
    account_number = models.CharField(max_length=40)
    routing_number = models.CharField(max_length=30, blank=True)
    branch_name = models.CharField(max_length=150, blank=True)
    swift_code = models.CharField(max_length=20, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "bank_name"]

    def __str__(self):
        return f"{self.bank_name} ({self.account_number})"


class MobileBankingAgent(TimeStampedModel):
    provider = models.CharField(max_length=40, help_text="e.g. bKash, Nagad")
    agent_number = models.CharField(max_length=20)
    label = models.CharField(max_length=40, blank=True, help_text="e.g. Agent, Merchant")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "provider"]

    def __str__(self):
        return f"{self.provider} — {self.agent_number}"


class OfficialDocumentType(models.TextChoices):
    TRADE_LICENSE = "trade_license", "Trade License"
    TIN = "tin", "TIN Certificate"
    BIN = "bin", "BIN Certificate"
    INCORPORATION = "incorporation", "Certificate of Incorporation"


class OfficialDocument(TimeStampedModel):
    """Internal record only -- deliberately has no serializer/viewset/API route.
    Only ever reachable via Django admin (staff login required). See
    apps.core.storage.get_raw_file_storage for the storage/privacy tradeoffs."""

    doc_type = models.CharField(max_length=30, choices=OfficialDocumentType.choices)
    reference_number = models.CharField(max_length=100, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    file = models.FileField(
        upload_to="advergo/official_documents/", storage=get_raw_file_storage, blank=True, null=True
    )
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["doc_type"]

    def __str__(self):
        return self.get_doc_type_display()
