from rest_framework import serializers

from core.constants import DEFAULT_CURRENCY
from .models import Listing


class ListingSerializer(serializers.ModelSerializer):
    """Serializes a listing. landlord is read-only (set automatically in
    perform_create, never by the client); price_display adds a formatted
    string alongside the raw price for convenience.
    """
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

    def validate(self, attrs):
        """Duplicates the DB-level UniqueConstraint check here, because DRF
            cannot auto-generate a validator for a *conditional* constraint
            (condition=Q(is_deleted=False)). Without this, a duplicate address
            would raise an unhandled IntegrityError (500) instead of a clean 400.
        """
        request = self.context['request']
        city = attrs.get('city') or (self.instance.city if self.instance else None)
        street_address = attrs.get('street_address') or (self.instance.street_address if self.instance else None)

        queryset = Listing.objects.filter(
            landlord=request.user,
            city=city,
            street_address=street_address,
        )
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                'You already have an active listing at this address.'
            )

        return attrs