from django.db import models
from django.conf import settings

from apps.listings.models import Listing


class SearchQuery(models.Model):
    query_text = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.query_text

class ViewHistory(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='views')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='listing_views',
        null=True,
        blank=True,
    )
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-viewed_at']
        constraints = [
            models.UniqueConstraint(
                fields=['listing', 'user'],
                condition=models.Q(user__isnull=False),
                name='unique_listing_view_per_user',
            ),
        ]

    def __str__(self):
        return f'{self.listing} — {self.viewed_at}'