from django.conf import settings
from django.db import models

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
    price = models.DecimalField(max_digits=10, decimal_places=2)
    rooms = models.PositiveSmallIntegerField()
    property_type = models.CharField(max_length=20, choices=PropertyType.choices)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Listing'
        verbose_name_plural = 'Listings'

    def __str__(self):
        return self.title


