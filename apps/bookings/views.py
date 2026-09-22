from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.choices import Status as BookingStatus
from core.constants import MIN_BOOKING_CANCEL_ADVANCE_DAYS
from core.permissions import IsTenant
from .models import Booking
from .permissions import IsBookingTenant, IsBookingLandlord
from .serializers import BookingSerializer


class BookingViewSet(viewsets.ModelViewSet):
    """Booking CRUD plus status-transition actions.

        Visibility and permissions differ by role: a tenant only sees/creates
        their own bookings; a landlord only sees bookings on their own listings
        and can only confirm/reject them, never create or cancel.
    """
    serializer_class = BookingSerializer
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        """Tenants see their own bookings; landlords see bookings made on their listings."""
        user = self.request.user
        if user.is_landlord:
            return Booking.objects.filter(listing__landlord=user)
        return Booking.objects.filter(tenant=user)

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated(), IsTenant()]
        if self.action == 'cancel':
            return [permissions.IsAuthenticated(), IsBookingTenant()]
        if self.action in ('confirm', 'reject'):
            return [permissions.IsAuthenticated(), IsBookingLandlord()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        listing = serializer.validated_data['listing']
        with transaction.atomic():
            Booking.objects.select_for_update().filter(listing=listing).exists()
            serializer.save(
                tenant=self.request.user,
                price_per_night=listing.price,
            )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Tenant-only: cancel a pending or confirmed booking, allowed only
                if at least MIN_BOOKING_CANCEL_ADVANCE_DAYS remain before check-in.
        """
        booking = self.get_object()

        if booking.status not in (BookingStatus.PENDING, BookingStatus.CONFIRMED):
            return Response(
                {'detail': 'This booking cannot be cancelled.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if booking.start_date < (timezone.now().date() + timedelta(days=MIN_BOOKING_CANCEL_ADVANCE_DAYS)):
            return Response(
                {'detail': f'Cancellation is only allowed at least {MIN_BOOKING_CANCEL_ADVANCE_DAYS} '
                           f'days before check-in.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.status = BookingStatus.CANCELLED
        booking.save()
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Landlord-only: accept a pending booking request."""
        booking = self.get_object()

        if booking.status != BookingStatus.PENDING:
            return Response(
                {'detail': 'Only pending bookings can be confirmed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.status = BookingStatus.CONFIRMED
        booking.save()
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Landlord-only: decline a pending booking request."""
        booking = self.get_object()

        if booking.status != BookingStatus.PENDING:
            return Response(
                {'detail': 'Only pending bookings can be rejected.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.status = BookingStatus.REJECTED
        booking.save()
        return Response(BookingSerializer(booking).data)