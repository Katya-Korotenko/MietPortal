from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from core.choices import Status
from core.constants import TENANT_GROUP, LANDLORD_GROUP
from apps.listings.models import Listing
from .models import Booking

User = get_user_model()


class BookingTestBase(APITestCase):
    """Shared setup for all booking tests."""

    def setUp(self):
        self.tenant_group, _ = Group.objects.get_or_create(name=TENANT_GROUP)
        self.landlord_group, _ = Group.objects.get_or_create(name=LANDLORD_GROUP)

        self.tenant = User.objects.create_user(
            username='tenant1', email='tenant1@example.com', password='StrongPass123'
        )
        self.tenant.groups.add(self.tenant_group)

        self.landlord = User.objects.create_user(
            username='landlord1', email='landlord1@example.com', password='StrongPass123'
        )
        self.landlord.groups.add(self.landlord_group)

        self.other_landlord = User.objects.create_user(
            username='landlord2', email='landlord2@example.com', password='StrongPass123'
        )
        self.other_landlord.groups.add(self.landlord_group)

        self.listing = Listing.objects.create(
            landlord=self.landlord,
            title='Cozy studio',
            description='Nice place',
            city='Berlin',
            street_address='Musterstraße 1',
            price=800,
            rooms=1,
            property_type='studio',
        )

        self.valid_start = timezone.now().date() + timedelta(days=10)
        self.valid_end = self.valid_start + timedelta(days=5)

    def booking_payload(self, **overrides):
        payload = {
            'listing': self.listing.id,
            'start_date': str(self.valid_start),
            'end_date': str(self.valid_end),
        }
        payload.update(overrides)
        return payload

class BookingCreateValidationTests(BookingTestBase):
    """Tests for validation rules when creating a booking."""

    def authenticate_as(self, user):
        self.client.force_authenticate(user=user)

    def test_tenant_can_create_valid_booking(self):
        self.authenticate_as(self.tenant)
        response = self.client.post('/api/bookings/', self.booking_payload())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Booking.objects.count(), 1)

    def test_landlord_cannot_create_booking(self):
        self.authenticate_as(self.landlord)
        response = self.client.post('/api/bookings/', self.booking_payload())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_landlord_cannot_book_own_listing(self):
        self.landlord.groups.add(self.tenant_group)
        self.authenticate_as(self.landlord)
        response = self.client.post('/api/bookings/', self.booking_payload())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_book_inactive_listing(self):
        self.listing.is_active = False
        self.listing.save()
        self.authenticate_as(self.tenant)
        response = self.client.post('/api/bookings/', self.booking_payload())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_end_date_must_be_after_start_date(self):
        self.authenticate_as(self.tenant)
        payload = self.booking_payload(
            start_date=str(self.valid_end),
            end_date=str(self.valid_start),
        )
        response = self.client.post('/api/bookings/', payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_book_less_than_7_days_in_advance(self):
        self.authenticate_as(self.tenant)
        too_soon = timezone.now().date() + timedelta(days=3)
        payload = self.booking_payload(
            start_date=str(too_soon),
            end_date=str(too_soon + timedelta(days=2)),
        )
        response = self.client.post('/api/bookings/', payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_book_more_than_1_year_in_advance(self):
        self.authenticate_as(self.tenant)
        too_far = timezone.now().date() + timedelta(days=400)
        payload = self.booking_payload(
            start_date=str(too_far),
            end_date=str(too_far + timedelta(days=2)),
        )
        response = self.client.post('/api/bookings/', payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_book_overlapping_dates(self):
        Booking.objects.create(
            listing=self.listing,
            tenant=self.tenant,
            start_date=self.valid_start,
            end_date=self.valid_end,
        )
        self.authenticate_as(self.tenant)
        overlapping_start = self.valid_start + timedelta(days=2)
        overlapping_end = self.valid_end + timedelta(days=2)
        payload = self.booking_payload(
            start_date=str(overlapping_start),
            end_date=str(overlapping_end),
        )
        response = self.client.post('/api/bookings/', payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_anonymous_user_cannot_create_booking(self):
        response = self.client.post('/api/bookings/', self.booking_payload())
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class BookingActionsTests(BookingTestBase):
    """Tests for confirm/reject/cancel actions and related permissions."""

    def authenticate_as(self, user):
        self.client.force_authenticate(user=user)

    def create_pending_booking(self, start_date=None, end_date=None):
        return Booking.objects.create(
            listing=self.listing,
            tenant=self.tenant,
            start_date=start_date or self.valid_start,
            end_date=end_date or self.valid_end,
            status=Status.PENDING,
        )

    # --- confirm ---

    def test_landlord_can_confirm_pending_booking(self):
        booking = self.create_pending_booking()
        self.authenticate_as(self.landlord)
        response = self.client.post(f'/api/bookings/{booking.id}/confirm/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Status.CONFIRMED)

    def test_other_landlord_cannot_confirm_booking(self):
        """403 or 404 are both acceptable — either the permission check rejects
            the request, or the booking simply isn't in this landlord's queryset."""
        booking = self.create_pending_booking()
        self.authenticate_as(self.other_landlord)
        response = self.client.post(f'/api/bookings/{booking.id}/confirm/')
        self.assertIn(response.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

    def test_tenant_cannot_confirm_own_booking(self):
        """403 or 404 are both acceptable, same reasoning as above."""
        booking = self.create_pending_booking()
        self.authenticate_as(self.tenant)
        response = self.client.post(f'/api/bookings/{booking.id}/confirm/')
        self.assertIn(response.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

    def test_cannot_confirm_already_confirmed_booking(self):
        booking = self.create_pending_booking()
        booking.status = Status.CONFIRMED
        booking.save()
        self.authenticate_as(self.landlord)
        response = self.client.post(f'/api/bookings/{booking.id}/confirm/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- reject ---

    def test_landlord_can_reject_pending_booking(self):
        booking = self.create_pending_booking()
        self.authenticate_as(self.landlord)
        response = self.client.post(f'/api/bookings/{booking.id}/reject/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Status.REJECTED)

    # --- cancel ---

    def test_tenant_can_cancel_booking_far_enough_in_advance(self):
        booking = self.create_pending_booking()
        self.authenticate_as(self.tenant)
        response = self.client.post(f'/api/bookings/{booking.id}/cancel/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Status.CANCELLED)

    def test_tenant_cannot_cancel_booking_less_than_7_days_before_start(self):
        near_start = timezone.now().date() + timedelta(days=3)
        booking = self.create_pending_booking(
            start_date=near_start, end_date=near_start + timedelta(days=2)
        )
        self.authenticate_as(self.tenant)
        response = self.client.post(f'/api/bookings/{booking.id}/cancel/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_landlord_cannot_cancel_tenants_booking(self):
        """403 or 404 are both acceptable, same reasoning as above."""
        booking = self.create_pending_booking()
        self.authenticate_as(self.landlord)
        response = self.client.post(f'/api/bookings/{booking.id}/cancel/')
        self.assertIn(response.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

    # --- queryset visibility ---

    def test_tenant_sees_only_own_bookings(self):
        other_tenant = User.objects.create_user(
            username='tenant2', email='tenant2@example.com', password='StrongPass123'
        )
        other_tenant.groups.add(self.tenant_group)
        self.create_pending_booking()
        Booking.objects.create(
            listing=self.listing,
            tenant=other_tenant,
            start_date=self.valid_start,
            end_date=self.valid_end,
        )
        self.authenticate_as(self.tenant)
        response = self.client.get('/api/bookings/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 1)

    # --- direct HTTP methods disabled ---

    def test_put_is_not_allowed(self):
        booking = self.create_pending_booking()
        self.authenticate_as(self.tenant)
        response = self.client.put(f'/api/bookings/{booking.id}/', self.booking_payload())
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_patch_is_not_allowed(self):
        booking = self.create_pending_booking()
        self.authenticate_as(self.tenant)
        response = self.client.patch(f'/api/bookings/{booking.id}/',
                                     {'end_date': str(self.valid_end + timedelta(days=1))})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_is_not_allowed(self):
        booking = self.create_pending_booking()
        self.authenticate_as(self.tenant)
        response = self.client.delete(f'/api/bookings/{booking.id}/')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_landlord_cannot_bypass_confirm_via_patch(self):
        """Even the listing's own landlord must go through the confirm/reject actions —
        direct PATCH to change status must be blocked at the HTTP method level."""
        booking = self.create_pending_booking()
        self.authenticate_as(self.landlord)
        response = self.client.patch(f'/api/bookings/{booking.id}/', {'status': 'confirmed'})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)