from rest_framework import serializers

from core.constants import DEFAULT_CURRENCY
from .models import Listing


class ListingSerializer(serializers.ModelSerializer):
    price_display = serializers.SerializerMethodField()
    landlord = serializers.ReadOnlyField(source='landlord.username')

    class Meta:
        model = Listing
        fields = (
        'id', 'landlord', 'title', 'description', 'city', 'district',
        'street_address', 'price', 'price_display', 'rooms',
        'property_type', 'is_active', 'created_at', 'updated_at',
    )
        read_only_fields = ('id', 'landlord', 'created_at', 'updated_at')

    def get_price_display(self, obj):
        return f'{obj.price} {DEFAULT_CURRENCY}'