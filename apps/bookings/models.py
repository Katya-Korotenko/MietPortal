from django.db import models
from django.conf import settings
from django.db import models

from apps.listings.models import Listing


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        REJECTED = 'rejected', 'Rejected'
        CANCELLED = 'cancelled', 'Cancelled'

    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='bookings',
    )

    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.listing} ({self.start_date} — {self.end_date})'
