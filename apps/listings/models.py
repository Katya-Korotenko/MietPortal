from django.conf import settings
from django.db import models


class Listing(models.Model):
    class PropertyType(models.TextChoices):
        APARTMENT = 'apartment', 'Квартира'
        HOUSE = 'house', 'Дом'
        STUDIO = 'studio', 'Студия'

    title = models.CharField(max_length=255)
    description = models.TextField()
    city = models.CharField(max_length=100)
    district = models.CharField(max_length=100, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    rooms = models.PositiveSmallIntegerField()
    property_type = models.CharField(max_length=20, choices=PropertyType.choices)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title