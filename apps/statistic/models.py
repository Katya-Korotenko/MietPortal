from django.db import models
from django.conf import settings

from apps.listings.models import Listing


class SearchQuery(models.Model):
    """A single logged search term (normalized: stripped and lowercased
        before saving), used to compute the most popular searches.
    """
    query_text = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Search Query'
        verbose_name_plural = 'Search Queries'

    def __str__(self):
        return self.query_text

class ViewHistory(models.Model):
    """A single view of a listing.

        The unique constraint only applies when user is set — an authenticated
        user's repeat views of the same listing are deduplicated, but anonymous
        views (user=None) are never deduplicated, since anonymous visitors can't
        be told apart from one another.
    """
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