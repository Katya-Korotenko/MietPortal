from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from simple_history.models import HistoricalRecords

from core.choices import Status
from core.models import TimeStampedModel


class Booking(TimeStampedModel):
    """A tenant's reservation for a listing over a date range.

        listing/tenant use PROTECT instead of CASCADE so that deleting a listing
        or a user never silently destroys booking history. Status transitions
        (confirm/reject/cancel) are handled in the view, not here.
    """

    listing = models.ForeignKey(
        'listings.Listing',
        on_delete=models.PROTECT,
        related_name='bookings',
    )
    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='bookings',
    )
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(1.00)])
    history = HistoricalRecords()

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Booking'
        verbose_name_plural = 'Bookings'

    def __str__(self):
        return f'{self.listing} ({self.start_date} — {self.end_date})'