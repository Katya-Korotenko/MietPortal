from django.utils import timezone
from rest_framework import serializers

from core.choices import Status
from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    """Serializes a review. tenant/listing are read-only convenience fields
    pulled through the booking relation for display purposes. All eligibility
    rules for creating a review live in validate_booking(), not here.
    """
    tenant = serializers.ReadOnlyField(source='booking.tenant.username')
    listing = serializers.ReadOnlyField(source='booking.listing.title')

    class Meta:
        model = Review
        fields = ('id', 'booking', 'tenant', 'listing', 'rating', 'comment', 'created_at')
        read_only_fields = ('id', 'created_at')

    def validate_booking(self, booking):
        """Enforces all review eligibility rules: must be the booking's own
            tenant, the booking must be confirmed, its end_date must have passed
            (same day counts as passed), and it must not already have a review.
        """
        request = self.context['request']

        if booking.tenant != request.user:
            raise serializers.ValidationError('You can only review your own bookings.')

        if booking.status != Status.CONFIRMED:
            raise serializers.ValidationError('You can only review confirmed bookings.')

        if booking.end_date > timezone.now().date():
            raise serializers.ValidationError('You can only review a booking after it has ended.')

        if hasattr(booking, 'review'):
            raise serializers.ValidationError('This booking has already been reviewed.')

        return booking