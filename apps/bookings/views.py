from datetime import timedelta

from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.choices import Status as BookingStatus
from core.permissions import IsTenant
from .models import Booking
from .permissions import IsBookingTenant, IsBookingLandlord
from .serializers import BookingSerializer


class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer

    def get_queryset(self):
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
        serializer.save(tenant=self.request.user)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        booking = self.get_object()

        if booking.status not in (BookingStatus.PENDING, BookingStatus.CONFIRMED):
            return Response(
                {'detail': 'This booking cannot be cancelled.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if booking.start_date < (timezone.now().date() + timedelta(days=7)):
            return Response(
                {'detail': 'Cancellation is only allowed at least 7 days before check-in.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.status = BookingStatus.CANCELLED
        booking.save()
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
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
        booking = self.get_object()

        if booking.status != BookingStatus.PENDING:
            return Response(
                {'detail': 'Only pending bookings can be rejected.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.status = BookingStatus.REJECTED
        booking.save()
        return Response(BookingSerializer(booking).data)