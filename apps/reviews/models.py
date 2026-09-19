from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.bookings.models import Booking


class Review(models.Model):
    """A review left by a tenant for a completed booking.

        Linked to Booking (not directly to Listing/User) so that the same tenant
        can leave a separate review for each distinct stay, while OneToOneField
        guarantees at most one review per booking. All eligibility rules (must be
        the tenant, must be confirmed, must have ended) live in the serializer's
        validate_booking(), not here.
    """
    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name='review',
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'

    def __str__(self):
        return f'{self.booking} — {self.rating}'