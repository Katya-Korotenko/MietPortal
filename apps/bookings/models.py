from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from core.choices import Status


class Booking(models.Model):
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Booking'
        verbose_name_plural = 'Bookings'

    def __str__(self):
        return f'{self.listing} ({self.start_date} — {self.end_date})'