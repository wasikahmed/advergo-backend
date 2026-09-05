import uuid

from django.db import models


class TimeStampedModel(models.Model):
    """Adds a UUID primary key plus created_at/updated_at to any model that
    inherits it. UUIDs keep row identifiers non-enumerable (an order/invoice
    id can't be guessed by incrementing a number) and safe to expose directly
    in API URLs.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(deleted_at__isnull=True)


class SoftDeleteManager(models.Manager):
    # Without this, a model whose only manager is this one has NO manager at
    # all in a data migration's historical model state (Django only carries
    # a manager into migrations if some manager on the model opts in) --
    # `SomeModel.objects` then raises AttributeError, but only on a fresh
    # database where every migration actually runs top to bottom (exactly
    # what CI's throwaway Postgres does, unlike a long-lived dev DB where
    # this migration already ran once and never gets replayed).
    use_in_migrations = True

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).alive()


class SoftDeleteModel(models.Model):
    """
    Marks a row deleted instead of removing it -- needed for anything that
    might be referenced by an order/invoice history (products, fabrics)
    so past orders keep a valid reference after a catalog item is retired.
    """

    deleted_at = models.DateTimeField(null=True, blank=True)

    all_objects = models.Manager()
    objects = SoftDeleteManager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        from django.utils import timezone

        self.deleted_at = timezone.now()
        self.save(using=using, update_fields=["deleted_at"])

    def hard_delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)
