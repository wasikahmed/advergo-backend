from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


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
    image = models.ImageField(upload_to="banners/", blank=True, null=True)
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


class Achievement(TimeStampedModel):
    icon = models.CharField(max_length=8, blank=True, help_text="Emoji shown in the UI.")
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
    # External URL (e.g. Clearbit's logo API) by design -- not something we host ourselves.
    logo_url = models.URLField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


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


class GalleryCategory(models.TextChoices):
    FACTORY = "factory", "Factory"
    CLIENTS = "clients", "Clients"


class GalleryItem(TimeStampedModel):
    image = models.ImageField(upload_to="gallery/", blank=True, null=True)
    label = models.CharField(max_length=120)
    category = models.CharField(max_length=10, choices=GalleryCategory.choices)
    description = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "-created_at"]

    def __str__(self):
        return self.label


class CompanyInfo(TimeStampedModel):
    """Singleton -- always exactly one row (pk=1)."""

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

    class Meta:
        verbose_name = verbose_name_plural = "company info"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # singleton: never actually deletable from the admin

    def __str__(self):
        return self.name
