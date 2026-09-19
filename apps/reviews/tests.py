from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from core.constants import TENANT_GROUP, LANDLORD_GROUP
from core.choices import Status
from apps.listings.models import Listing
from apps.bookings.models import Booking
from .models import Review

User = get_user_model()


class ReviewTestBase(APITestCase):
    """Shared setup for all review tests."""

    def setUp(self):
        """Sets up three bookings covering the three ways a review can be
            rejected: not yet ended (future_booking), never confirmed
            (pending_past_booking) — plus one valid, reviewable booking (past_booking).
        """
        self.tenant_group, _ = Group.objects.get_or_create(name=TENANT_GROUP)
        self.landlord_group, _ = Group.objects.get_or_create(name=LANDLORD_GROUP)

        self.tenant = User.objects.create_user(
            username='tenant1', email='tenant1@example.com', password='StrongPass123'
        )
        self.tenant.groups.add(self.tenant_group)

        self.other_tenant = User.objects.create_user(
            username='tenant2', email='tenant2@example.com', password='StrongPass123'
        )
        self.other_tenant.groups.add(self.tenant_group)

        self.landlord = User.objects.create_user(
            username='landlord1', email='landlord1@example.com', password='StrongPass123'
        )
        self.landlord.groups.add(self.landlord_group)

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

        self.past_booking = Booking.objects.create(
            listing=self.listing,
            tenant=self.tenant,
            start_date=timezone.now().date() - timedelta(days=20),
            end_date=timezone.now().date() - timedelta(days=10),
            status=Status.CONFIRMED,
        )

        self.future_booking = Booking.objects.create(
            listing=self.listing,
            tenant=self.tenant,
            start_date=timezone.now().date() + timedelta(days=30),
            end_date=timezone.now().date() + timedelta(days=40),
            status=Status.CONFIRMED,
        )

        self.pending_past_booking = Booking.objects.create(
            listing=self.listing,
            tenant=self.tenant,
            start_date=timezone.now().date() - timedelta(days=20),
            end_date=timezone.now().date() - timedelta(days=10),
            status=Status.PENDING,
        )

    def authenticate_as(self, user):
        self.client.force_authenticate(user=user)

class ReviewCreateTests(ReviewTestBase):
    """Tests for review creation validation."""

    def test_tenant_can_review_completed_confirmed_booking(self):
        self.authenticate_as(self.tenant)
        response = self.client.post('/api/reviews/', {
            'booking': self.past_booking.id,
            'rating': 5,
            'comment': 'Great stay!',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_cannot_review_booking_that_has_not_ended(self):
        self.authenticate_as(self.tenant)
        response = self.client.post('/api/reviews/', {
            'booking': self.future_booking.id,
            'rating': 5,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_review_non_confirmed_booking(self):
        self.authenticate_as(self.tenant)
        response = self.client.post('/api/reviews/', {
            'booking': self.pending_past_booking.id,
            'rating': 5,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_review_someone_elses_booking(self):
        self.authenticate_as(self.other_tenant)
        response = self.client.post('/api/reviews/', {
            'booking': self.past_booking.id,
            'rating': 5,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_review_same_booking_twice(self):
        self.authenticate_as(self.tenant)
        self.client.post('/api/reviews/', {'booking': self.past_booking.id, 'rating': 5})
        response = self.client.post('/api/reviews/', {'booking': self.past_booking.id, 'rating': 3})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rating_must_be_between_1_and_5(self):
        self.authenticate_as(self.tenant)
        response = self.client.post('/api/reviews/', {'booking': self.past_booking.id, 'rating': 6})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_anonymous_cannot_create_review(self):
        response = self.client.post('/api/reviews/', {'booking': self.past_booking.id, 'rating': 5})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class ReviewUpdateDeleteVisibilityTests(ReviewTestBase):
    """Tests for review immutability, deletion, and listing filter."""

    def setUp(self):
        super().setUp()
        self.authenticate_as(self.tenant)
        response = self.client.post('/api/reviews/', {
            'booking': self.past_booking.id,
            'rating': 4,
            'comment': 'Good experience',
        })
        self.review_id = response.data['id']
        self.client.force_authenticate(user=None)

    def test_put_is_not_allowed(self):
        self.authenticate_as(self.tenant)
        response = self.client.put(f'/api/reviews/{self.review_id}/', {'rating': 5})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_patch_is_not_allowed(self):
        self.authenticate_as(self.tenant)
        response = self.client.patch(f'/api/reviews/{self.review_id}/', {'rating': 5})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_owner_can_delete_review(self):
        self.authenticate_as(self.tenant)
        response = self.client.delete(f'/api/reviews/{self.review_id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Review.objects.filter(id=self.review_id).exists())

    def test_other_user_cannot_delete_review(self):
        self.authenticate_as(self.other_tenant)
        response = self.client.delete(f'/api/reviews/{self.review_id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anyone_can_read_reviews_without_auth(self):
        response = self.client.get('/api/reviews/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_reviews_by_listing(self):
        other_listing = Listing.objects.create(
            landlord=self.landlord,
            title='Another place',
            description='Different listing',
            city='Munich',
            street_address='Andere Straße 2',
            price=900,
            rooms=2,
            property_type='apartment',
        )
        response = self.client.get(f'/api/reviews/?listing={other_listing.id}')
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 0)

        response = self.client.get(f'/api/reviews/?listing={self.listing.id}')
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.review_id)