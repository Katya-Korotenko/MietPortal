from django.db import models
from django.utils import timezone
import uuid

class UniqueID(models.Model):
    """Replaces the default auto-incrementing integer id with a UUID, so that
        object IDs are not sequentially guessable (e.g. exposed via /api/users/1/,
        /api/users/2/...). Used on User at the model's teacher's request.
    """
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4,
                          verbose_name='UUID id')

    class Meta:
        abstract = True

class TimeStampedModel(models.Model):
    """Adds created_at/updated_at to any model that inherits it, so these
        two fields are never redefined by hand in each app's models.py.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True



class SoftDeleteQuerySet(models.QuerySet):
    """Lets code explicitly ask for only alive or only dead rows, e.g.
        Listing.objects.dead() to inspect soft-deleted records without
        bypassing the manager entirely.
    """
    def alive(self):
        return self.filter(is_deleted=False)

    def dead(self):
        return self.filter(is_deleted=True)


class SoftDeleteManager(models.Manager):
    """The default manager (`objects`) for soft-deletable models — always
        hides is_deleted=True rows. Use `all_objects` (defined below) when you
        need to see everything, including deleted records.
    """
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)


class SoftDeleteModel(models.Model):
    """Makes .delete() non-destructive: instead of removing the row, it sets
        is_deleted=True and stamps deleted_at. This preserves foreign-key history
        (bookings, reviews, etc.) that would otherwise be lost or cascade-deleted.
        Use `all_objects` to bypass the filter, or `hard_delete()` for a real,
        permanent deletion when one is genuinely needed.
    """
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """Soft delete: marks the row as deleted instead of removing it."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(using=using)

    def hard_delete(self, using=None, keep_parents=False):
        """Permanently removes the row from the database. Use with care —
            this bypasses soft delete entirely."""
        super().delete(using=using, keep_parents=keep_parents)
