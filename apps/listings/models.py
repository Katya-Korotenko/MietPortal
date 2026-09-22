from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Case, Value, When

from core.choices import PropertyType
from core.models import TimeStampedModel, SoftDeleteModel


class Listing(TimeStampedModel, SoftDeleteModel):
    """A rental property listing owned by a landlord.
    Uses soft delete so that removing a listing never breaks the history of
    bookings/reviews tied to it. The unique constraint on
    (landlord, city, street_address) only applies to non-deleted listings,
    so a landlord can re-list at the same address after deleting the old one.
    """
    landlord = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='listings',
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    city = models.CharField(max_length=100)
    district = models.CharField(max_length=100, blank=True, null=True)
    street_address = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(1.00)])
    rooms = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(10)])
    property_type = models.CharField(max_length=20, choices=PropertyType.choices)
    is_active = models.BooleanField(default=True)
    # MySQL has no partial indexes, so the unique constraint can't use condition=.
    # Instead, active_key is 1 for non-deleted rows and NULL for deleted ones.
    # NULLs never collide in a unique index, so the constraint below
    # effectively applies only to active listings.
    active_key = models.GeneratedField(
        expression=Case(
            When(is_deleted=False, then=Value(1)),
            default=Value(None),
            output_field=models.IntegerField(),
        ),
        output_field=models.IntegerField(null=True),
        db_persist=True,
    )
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Listing'
        verbose_name_plural = 'Listings'
        indexes = [
            models.Index(fields=['city']),
            models.Index(fields=['price']),
            models.Index(fields=['rooms']),
            models.Index(fields=['property_type']),
        ]
        constraints = [
        models.UniqueConstraint(
            fields=['landlord', 'city', 'street_address', 'active_key'],
            name='unique_active_listing_per_address',
        )
    ]
    def __str__(self):
        return self.title


