from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from core.choices import PropertyType
from core.models import TimeStampedModel, SoftDeleteModel


class Listing(TimeStampedModel, SoftDeleteModel):
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
    rooms = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    property_type = models.CharField(max_length=20, choices=PropertyType.choices)
    is_active = models.BooleanField(default=True)
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
            fields=['city', 'street_address'],
            condition=models.Q(is_deleted=False),
            name='unique_active_listing_per_address',
        )
    ]
    def __str__(self):
        return self.title


