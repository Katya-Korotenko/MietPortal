from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.test import APITestCase

from core.constants import LANDLORD_GROUP
from apps.listings.models import Listing
from .models import SearchQuery, ViewHistory

User = get_user_model()


class StatisticTestBase(APITestCase):
    """Shared setup for statistic tests."""

    def setUp(self):
        self.landlord_group, _ = Group.objects.get_or_create(name=LANDLORD_GROUP)

        self.landlord = User.objects.create_user(
            username='landlord1', email='landlord1@example.com', password='StrongPass123'
        )
        self.landlord.groups.add(self.landlord_group)

        self.user = User.objects.create_user(
            username='viewer1', email='viewer1@example.com', password='StrongPass123'
        )

        self.listing1 = Listing.objects.create(
            landlord=self.landlord,
            title='Cozy studio with balcony',
            description='Nice place',
            city='Berlin',
            street_address='Musterstraße 1',
            price=800,
            rooms=1,
            property_type='studio',
        )
        self.listing2 = Listing.objects.create(
            landlord=self.landlord,
            title='Family house',
            description='Quiet area',
            city='Munich',
            street_address='Hauptstraße 5',
            price=1500,
            rooms=4,
            property_type='house',
        )

    def authenticate_as(self, user):
        self.client.force_authenticate(user=user)


class ViewHistoryTests(StatisticTestBase):
    """Tests for automatic view tracking on listing retrieve."""

    def test_viewing_listing_creates_view_history(self):
        self.authenticate_as(self.user)
        self.client.get(f'/api/listings/{self.listing1.id}/')
        self.assertTrue(
            ViewHistory.objects.filter(listing=self.listing1, user=self.user).exists()
        )

    def test_repeated_view_by_same_user_does_not_duplicate(self):
        """Enforces the 'don't count a repeat view from the same person' rule."""
        self.authenticate_as(self.user)
        self.client.get(f'/api/listings/{self.listing1.id}/')
        self.client.get(f'/api/listings/{self.listing1.id}/')
        count = ViewHistory.objects.filter(listing=self.listing1, user=self.user).count()
        self.assertEqual(count, 1)

    def test_anonymous_view_is_recorded_without_user(self):
        self.client.get(f'/api/listings/{self.listing1.id}/')
        self.assertTrue(
            ViewHistory.objects.filter(listing=self.listing1, user__isnull=True).exists()
        )

    def test_repeated_anonymous_views_are_each_recorded(self):
        """Anonymous views are NOT deduplicated by design — there's no way to
        tell two different anonymous visitors apart, so counting every hit is
        more honest than pretending to deduplicate them."""
        self.client.get(f'/api/listings/{self.listing1.id}/')
        self.client.get(f'/api/listings/{self.listing1.id}/')
        count = ViewHistory.objects.filter(listing=self.listing1, user__isnull=True).count()
        self.assertEqual(count, 2)


class SearchQueryTests(StatisticTestBase):
    """Tests for automatic search query logging on listing list."""

    def test_search_creates_search_query_record(self):
        self.client.get('/api/listings/?search=balcony')
        self.assertTrue(SearchQuery.objects.filter(query_text='balcony').exists())

    def test_search_text_is_normalized(self):
        self.client.get('/api/listings/?search=  Balcony  ')
        self.assertTrue(SearchQuery.objects.filter(query_text='balcony').exists())

    def test_listing_without_search_param_does_not_create_query(self):
        self.client.get('/api/listings/')
        self.assertEqual(SearchQuery.objects.count(), 0)

class PopularStatsEndpointsTests(StatisticTestBase):
    """Tests for popular_searches and popular_listings endpoints."""

    def test_popular_searches_orders_by_frequency(self):
        SearchQuery.objects.create(query_text='berlin')
        SearchQuery.objects.create(query_text='berlin')
        SearchQuery.objects.create(query_text='munich')

        response = self.client.get('/api/statistic/popular_searches/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['query_text'], 'berlin')
        self.assertEqual(response.data[0]['count'], 2)

    def test_popular_listings_orders_by_view_count(self):
        ViewHistory.objects.create(listing=self.listing1, user=self.user)

        other_user = User.objects.create_user(
            username='viewer2', email='viewer2@example.com', password='StrongPass123'
        )
        ViewHistory.objects.create(listing=self.listing1, user=other_user)
        ViewHistory.objects.create(listing=self.listing2, user=self.user)

        response = self.client.get('/api/statistic/popular_listings/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['title'], self.listing1.title)

    def test_stats_endpoints_accessible_without_auth(self):
        response = self.client.get('/api/statistic/popular_searches/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)