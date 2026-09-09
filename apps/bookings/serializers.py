from django.utils import timezone
from rest_framework import serializers

from core.choices import Status
from core.constants import DATE_INPUT_FORMATS
from .models import Booking



class BookingSerializer(serializers.ModelSerializer):
    tenant = serializers.ReadOnlyField(source='tenant.username')
    start_date = serializers.DateField(input_formats=DATE_INPUT_FORMATS)
    end_date = serializers.DateField(input_formats=DATE_INPUT_FORMATS)

    class Meta:
        model = Booking
        fields = (
            'id', 'listing', 'tenant', 'start_date', 'end_date',
            'status', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'status', 'created_at', 'updated_at')

    def validate(self, attrs):
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        listing = attrs.get('listing')

        if start_date >= end_date:
            raise serializers.ValidationError('End date must be after start date.')

        if start_date < timezone.now().date():
            raise serializers.ValidationError('Start date cannot be in the past.')

        overlapping = Booking.objects.filter(
            listing=listing,
            status__in=[Status.PENDING, Status.CONFIRMED],
            start_date__lt=end_date,
            end_date__gt=start_date,
        )
        if overlapping.exists():
            raise serializers.ValidationError('These dates are already booked for this listing.')

        return attrs