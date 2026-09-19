from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.bookings.models import Booking
from core.constants import TENANT_GROUP, LANDLORD_GROUP
from .models import Listing

User = get_user_model()


class ListingTestBase(APITestCase):
    """Shared setup for all listing tests."""

    def setUp(self):
        self.tenant_group, _ = Group.objects.get_or_create(name=TENANT_GROUP)
        self.landlord_group, _ = Group.objects.get_or_create(name=LANDLORD_GROUP)

        self.landlord = User.objects.create_user(
            username='landlord1', email='landlord1@example.com', password='StrongPass123'
        )
        self.landlord.groups.add(self.landlord_group)

        self.other_landlord = User.objects.create_user(
            username='landlord2', email='landlord2@example.com', password='StrongPass123'
        )
        self.other_landlord.groups.add(self.landlord_group)

        self.tenant = User.objects.create_user(
            username='tenant1', email='tenant1@example.com', password='StrongPass123'
        )
        self.tenant.groups.add(self.tenant_group)

        self.listing = Listing.objects.create(
            landlord=self.landlord,
            title='Cozy studio',
            description='Nice place near the park',
            city='Berlin',
            district='Mitte',
            street_address='Musterstraße 1',
            price=800,
            rooms=1,
            property_type='studio',
        )

    def authenticate_as(self, user):
        self.client.force_authenticate(user=user)

    def listing_payload(self, **overrides):
        payload = {
            'title': 'New apartment',
            'description': 'Bright and spacious',
            'city': 'Munich',
            'district': 'Schwabing',
            'street_address': 'Beispielstraße 5',
            'price': 1200,
            'rooms': 2,
            'property_type': 'apartment',
        }
        payload.update(overrides)
        return payload


class ListingCreateTests(ListingTestBase):
    """Tests for listing creation permissions and validation."""

    def test_landlord_can_create_listing(self):
        self.authenticate_as(self.landlord)
        response = self.client.post('/api/listings/', self.listing_payload())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['landlord'], self.landlord.username)

    def test_tenant_cannot_create_listing(self):
        self.authenticate_as(self.tenant)
        response = self.client.post('/api/listings/', self.listing_payload())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_create_listing(self):
        response = self.client.post('/api/listings/', self.listing_payload())
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_price_must_be_positive(self):
        self.authenticate_as(self.landlord)
        response = self.client.post('/api/listings/', self.listing_payload(price=0))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_price_cannot_be_negative(self):
        self.authenticate_as(self.landlord)
        response = self.client.post('/api/listings/', self.listing_payload(price=-100))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rooms_must_be_at_least_1(self):
        self.authenticate_as(self.landlord)
        response = self.client.post('/api/listings/', self.listing_payload(rooms=0))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_create_duplicate_active_listing_at_same_address(self):
        """Checks the serializer-level validation that mirrors the DB constraint —
            without it, this would raise an unhandled IntegrityError instead of 400."""
        self.authenticate_as(self.landlord)
        payload = self.listing_payload(
            city=self.listing.city,
            street_address=self.listing.street_address,
        )
        response = self.client.post('/api/listings/', payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_can_recreate_listing_at_same_address_after_soft_delete(self):
        """Confirms the condition=Q(is_deleted=False) behavior documented on the
        model: once the old listing is soft-deleted, its address is free again."""
        self.authenticate_as(self.landlord)
        self.client.delete(f'/api/listings/{self.listing.id}/')

        payload = self.listing_payload(
            city=self.listing.city,
            street_address=self.listing.street_address,
        )
        response = self.client.post('/api/listings/', payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_different_landlord_can_use_same_address(self):
        """The uniqueness constraint is scoped per-landlord (landlord, city,
        street_address) — a different landlord is free to list the same address."""
        self.authenticate_as(self.other_landlord)
        payload = self.listing_payload(
            city=self.listing.city,
            street_address=self.listing.street_address,
        )
        response = self.client.post('/api/listings/', payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

class ListingUpdateDeleteTests(ListingTestBase):
    """Tests for editing and deleting listings — ownership and soft delete."""

    def test_owner_can_update_listing(self):
        self.authenticate_as(self.landlord)
        response = self.client.patch(f'/api/listings/{self.listing.id}/', {'price': 900})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.price, 900)

    def test_other_landlord_cannot_update_listing(self):
        self.authenticate_as(self.other_landlord)
        response = self.client.patch(f'/api/listings/{self.listing.id}/', {'price': 900})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tenant_cannot_update_listing(self):
        self.authenticate_as(self.tenant)
        response = self.client.patch(f'/api/listings/{self.listing.id}/', {'price': 900})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anyone_can_read_listing_without_auth(self):
        response = self.client.get(f'/api/listings/{self.listing.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_owner_can_delete_listing(self):
        self.authenticate_as(self.landlord)
        response = self.client.delete(f'/api/listings/{self.listing.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_is_soft_not_hard(self):
        self.authenticate_as(self.landlord)
        self.client.delete(f'/api/listings/{self.listing.id}/')

        self.assertFalse(Listing.objects.filter(id=self.listing.id).exists())
        self.assertTrue(Listing.all_objects.filter(id=self.listing.id).exists())

        self.listing.refresh_from_db()
        self.assertTrue(self.listing.is_deleted)
        self.assertIsNotNone(self.listing.deleted_at)

    def test_other_landlord_cannot_delete_listing(self):
        self.authenticate_as(self.other_landlord)
        response = self.client.delete(f'/api/listings/{self.listing.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_deleted_listing_not_visible_in_list(self):
        self.authenticate_as(self.landlord)
        self.client.delete(f'/api/listings/{self.listing.id}/')

        response = self.client.get('/api/listings/')
        results = response.data.get('results', response.data)
        listing_ids = [item['id'] for item in results]
        self.assertNotIn(self.listing.id, listing_ids)

    def test_hard_delete_actually_removes_row(self):
        """Unlike a normal .delete() (soft delete), hard_delete() bypasses
        it entirely — the row is genuinely gone from the database."""
        listing_id = self.listing.id
        self.listing.hard_delete()

        self.assertFalse(Listing.objects.filter(id=listing_id).exists())
        self.assertFalse(Listing.all_objects.filter(id=listing_id).exists())

class ListingFilterSearchOrderingTests(ListingTestBase):
    """Tests for search, filtering and ordering on the listings endpoint."""

    def setUp(self):
        super().setUp()
        self.listing2 = Listing.objects.create(
            landlord=self.landlord,
            title='Spacious apartment with balcony',
            description='Great view',
            city='Berlin',
            district='Kreuzberg',
            street_address='Beispielweg 7',
            price=1200,
            rooms=3,
            property_type='apartment',
        )
        self.listing3 = Listing.objects.create(
            landlord=self.other_landlord,
            title='Family house',
            description='Quiet neighborhood',
            city='Munich',
            street_address='Hauptstraße 10',
            price=1800,
            rooms=4,
            property_type='house',
        )

    def get_results(self, response):
        return response.data.get('results', response.data)

    def test_filter_by_city(self):
        response = self.client.get('/api/listings/?city=Berlin')
        results = self.get_results(response)
        titles = {item['title'] for item in results}
        self.assertIn(self.listing.title, titles)
        self.assertIn(self.listing2.title, titles)
        self.assertNotIn(self.listing3.title, titles)

    def test_filter_by_property_type(self):
        response = self.client.get('/api/listings/?property_type=house')
        results = self.get_results(response)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], self.listing3.title)

    def test_filter_by_price_range(self):
        response = self.client.get('/api/listings/?min_price=1000&max_price=1500')
        results = self.get_results(response)
        titles = {item['title'] for item in results}
        self.assertEqual(titles, {self.listing2.title})

    def test_filter_by_rooms_range(self):
        response = self.client.get('/api/listings/?min_rooms=3&max_rooms=4')
        results = self.get_results(response)
        titles = {item['title'] for item in results}
        self.assertEqual(titles, {self.listing2.title, self.listing3.title})

    def test_search_by_keyword(self):
        response = self.client.get('/api/listings/?search=balcony')
        results = self.get_results(response)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], self.listing2.title)

    def test_ordering_by_price_ascending(self):
        response = self.client.get('/api/listings/?ordering=price')
        results = self.get_results(response)
        prices = [float(item['price']) for item in results]
        self.assertEqual(prices, sorted(prices))

    def test_ordering_by_price_descending(self):
        response = self.client.get('/api/listings/?ordering=-price')
        results = self.get_results(response)
        prices = [float(item['price']) for item in results]
        self.assertEqual(prices, sorted(prices, reverse=True))

    def test_combined_filters(self):
        response = self.client.get('/api/listings/?city=Berlin&min_price=1000')
        results = self.get_results(response)
        titles = {item['title'] for item in results}
        self.assertEqual(titles, {self.listing2.title})

class ListingVisibilityTests(ListingTestBase):
    """Tests for visibility rules combining is_active and soft delete."""

    def setUp(self):
        super().setUp()
        self.listing.is_active = False
        self.listing.save()

    # --- is_active=False scenarios ---

    def test_owner_can_see_own_inactive_listing(self):
        self.authenticate_as(self.landlord)
        response = self.client.get(f'/api/listings/{self.listing.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_tenant_with_booking_can_see_inactive_listing(self):
        Booking.objects.create(
            listing=self.listing,
            tenant=self.tenant,
            start_date=timezone.now().date() + timedelta(days=10),
            end_date=timezone.now().date() + timedelta(days=15),
        )
        self.authenticate_as(self.tenant)
        response = self.client.get(f'/api/listings/{self.listing.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_stranger_cannot_see_inactive_listing(self):
        stranger = User.objects.create_user(
            username='stranger', email='stranger@example.com', password='StrongPass123'
        )
        stranger.groups.add(self.tenant_group)
        self.authenticate_as(stranger)
        response = self.client.get(f'/api/listings/{self.listing.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_anonymous_cannot_see_inactive_listing(self):
        response = self.client.get(f'/api/listings/{self.listing.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_inactive_listing_hidden_from_public_list(self):
        response = self.client.get('/api/listings/')
        results = response.data.get('results', response.data)
        listing_ids = [item['id'] for item in results]
        self.assertNotIn(self.listing.id, listing_ids)

    # --- soft delete scenarios ---

    def test_owner_cannot_see_own_soft_deleted_listing(self):
        """Once the owner deletes their own listing, it disappears even for them —
        unlike is_active=False, soft delete is not meant to be toggled back casually."""
        self.authenticate_as(self.landlord)
        self.client.delete(f'/api/listings/{self.listing.id}/')

        response = self.client.get(f'/api/listings/{self.listing.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_tenant_with_booking_can_still_see_soft_deleted_listing(self):
        """A tenant who once booked this listing keeps access to it even after
        the landlord soft-deletes it, so their booking history stays meaningful."""
        Booking.objects.create(
            listing=self.listing,
            tenant=self.tenant,
            start_date=timezone.now().date() + timedelta(days=10),
            end_date=timezone.now().date() + timedelta(days=15),
        )
        self.authenticate_as(self.landlord)
        self.client.delete(f'/api/listings/{self.listing.id}/')

        self.authenticate_as(self.tenant)
        response = self.client.get(f'/api/listings/{self.listing.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_stranger_cannot_see_soft_deleted_listing(self):
        stranger = User.objects.create_user(
            username='stranger2', email='stranger2@example.com', password='StrongPass123'
        )
        stranger.groups.add(self.tenant_group)
        self.authenticate_as(self.landlord)
        self.client.delete(f'/api/listings/{self.listing.id}/')

        self.authenticate_as(stranger)
        response = self.client.get(f'/api/listings/{self.listing.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)