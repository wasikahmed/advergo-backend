from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.catalog.models import Product
from apps.core.models import TimeStampedModel


class ReviewStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class Review(TimeStampedModel):
    name = models.CharField(max_length=120)
    organization = models.CharField(max_length=150, blank=True)
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    text = models.TextField()
    status = models.CharField(
        max_length=10, choices=ReviewStatus.choices, default=ReviewStatus.PENDING
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.rating}★)"


class ProductReview(TimeStampedModel):
    """A logged-in customer's review of a specific product -- distinct from
    `Review`, which is a general company testimonial anyone can submit
    without an account. Moderated the same way (starts `pending`, staff
    approve/reject in /admin/) since a login only proves *an* account
    submitted it, not that the content is trustworthy."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="product_reviews")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="product_reviews"
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    text = models.TextField()
    status = models.CharField(
        max_length=10, choices=ReviewStatus.choices, default=ReviewStatus.PENDING
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "product"], name="unique_product_review_user_product"
            )
        ]

    def __str__(self):
        return f"{self.user} on {self.product} ({self.rating}★)"
