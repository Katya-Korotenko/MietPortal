from django.utils import timezone
from rest_framework import serializers

from core.choices import Status
from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    tenant = serializers.ReadOnlyField(source='booking.tenant.username')
    listing = serializers.ReadOnlyField(source='booking.listing.title')

    class Meta:
        model = Review
        fields = ('id', 'booking', 'tenant', 'listing', 'rating', 'comment', 'created_at')
        read_only_fields = ('id', 'created_at')

    def validate_booking(self, booking):
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