from django.db import models

from apps.listings.models import Listing


class SearchQuery(models.Model):
    query_text = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.query_text

class ViewHistory(models.Model):
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='views',
    )
    viewed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.listing} — {self.viewed_at}'