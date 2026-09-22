from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from core.choices import Status
from core.constants import DATE_INPUT_FORMATS, MAX_BOOKING_CREATE_ADVANCE_DAYS, MIN_BOOKING_CREATE_ADVANCE_DAYS
from .models import Booking



class BookingSerializer(serializers.ModelSerializer):
    """Serializes a booking. Accepts multiple date formats (see DATE_INPUT_FORMATS);
    status/id/timestamps are read-only — status changes only happen through
    the confirm/reject/cancel actions on the view, never via direct update.
    """
    tenant = serializers.ReadOnlyField(source='tenant.username')
    start_date = serializers.DateField(input_formats=DATE_INPUT_FORMATS)
    end_date = serializers.DateField(input_formats=DATE_INPUT_FORMATS)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = (
            'id', 'listing', 'tenant', 'start_date', 'end_date',
            'status', 'price_per_night', 'total_price', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'status',  'price_per_night', 'created_at', 'updated_at')

    def get_total_price(self, obj):
        nights = (obj.end_date - obj.start_date).days
        return obj.price_per_night * nights

    def validate(self, attrs):
        """Runs all booking-creation business rules together, since they depend
        on multiple fields at once (dates + listing) rather than a single field.
        """
        request = self.context['request']
        start_date = attrs.get('start_date') or (self.instance.start_date if self.instance else None)
        end_date = attrs.get('end_date') or (self.instance.end_date if self.instance else None)
        listing = attrs.get('listing') or (self.instance.listing if self.instance else None)

        if listing.landlord == request.user:
            raise serializers.ValidationError('You cannot book your own listing.')

        if not listing.is_active:
            raise serializers.ValidationError('This listing is currently not available for booking.')

        if start_date >= end_date:
            raise serializers.ValidationError('End date must be after start date.')

        if start_date < timezone.now().date() + timedelta(days=MIN_BOOKING_CREATE_ADVANCE_DAYS):
            raise serializers.ValidationError(f'Bookings must be made at least {MIN_BOOKING_CREATE_ADVANCE_DAYS} '
                                              f'days in advance.')

        if start_date > timezone.now().date() + timedelta(days=MAX_BOOKING_CREATE_ADVANCE_DAYS):
            raise serializers.ValidationError(f'Bookings cannot be made more than {MAX_BOOKING_CREATE_ADVANCE_DAYS} '
                                              f'days in advance.')

        overlapping = Booking.objects.filter(
            listing=listing,
            status__in=[Status.PENDING, Status.CONFIRMED],
            start_date__lt=end_date,
            end_date__gt=start_date,
        )
        if self.instance:
            overlapping = overlapping.exclude(pk=self.instance.pk)

        if overlapping.exists():
            raise serializers.ValidationError('These dates are already booked for this listing.')

        return attrs