import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction
from django.utils import timezone
from faker import Faker

from core.choices import PropertyType, Status
from core.constants import TENANT_GROUP, LANDLORD_GROUP
from apps.listings.models import Listing
from apps.bookings.models import Booking
from apps.reviews.models import Review
from apps.statistic.models import SearchQuery, ViewHistory

User = get_user_model()
fake = Faker('de_DE')  # German locale — fits the project's target market


class Command(BaseCommand):
    help = 'Populates the local database with fake data for development/demo purposes.'

    def add_arguments(self, parser):
        parser.add_argument('--landlords', type=int, default=5)
        parser.add_argument('--tenants', type=int, default=10)
        parser.add_argument('--listings-per-landlord', type=int, default=3)
        parser.add_argument('--flush', action='store_true', help='Delete existing seeded data first.')

    def handle(self, *args, **options):
        if options['flush']:
            self._flush()

        tenant_group, _ = Group.objects.get_or_create(name=TENANT_GROUP)
        landlord_group, _ = Group.objects.get_or_create(name=LANDLORD_GROUP)

        landlords = self._create_users(
            options['landlords'], landlord_group, prefix='landlord'
        )
        tenants = self._create_users(
            options['tenants'], tenant_group, prefix='tenant'
        )

        listings = self._create_listings(landlords, options['listings_per_landlord'])
        bookings = self._create_bookings(listings, tenants)
        self._create_reviews(bookings)
        self._create_view_history(listings, tenants)
        self._create_search_queries()

        self.stdout.write(self.style.SUCCESS(
            f'Seeded: {len(landlords)} landlords, {len(tenants)} tenants, '
            f'{len(listings)} listings, {len(bookings)} bookings.'
        ))

    # --- teardown -----------------------------------------------------------

    def _flush(self):
        """Deletes previously seeded data in dependency order (children before
        parents), so PROTECT on Booking.listing/Booking.tenant never blocks
        the cleanup. Uses Listing.all_objects (not the default soft-delete
        manager) so soft-deleted rows are also wiped, and QuerySet.delete()
        (not the model's overridden .delete()) so this is a real hard delete —
        Django's queryset delete always bypasses the per-instance override.
        """
        self.stdout.write('Flushing existing data...')
        ViewHistory.objects.all().delete()
        SearchQuery.objects.all().delete()
        Review.objects.all().delete()
        Booking.objects.all().delete()
        Listing.all_objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

    # --- users ----------------------------------------------------------------

    def _create_users(self, count, group, prefix):
        users = []
        for i in range(count):
            user = User.objects.create_user(
                username=f'{prefix}{i}',
                email=f'{prefix}{i}@example.com',
                password='TestPass123',
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                phone_number=f'+4917{random.randint(10000000, 99999999)}',
            )
            user.groups.add(group)
            users.append(user)
        return users

    # --- listings ---------------------------------------------------------------

    def _create_listings(self, landlords, per_landlord):
        """Creates `per_landlord` listings for each landlord.

        (landlord, city, street_address) is unique for non-deleted listings
        (see Listing.Meta.constraints), so a random Faker address can
        occasionally collide with one already used by the same landlord in
        the same city. Each attempt is wrapped in its own atomic block and
        retried with a fresh address on IntegrityError, instead of letting a
        rare collision abort the whole command partway through.
        """
        listings = []
        cities = ['Berlin', 'Munich', 'Hamburg', 'Cologne', 'Frankfurt']
        max_attempts = 5

        for landlord in landlords:
            for _ in range(per_landlord):
                for attempt in range(max_attempts):
                    try:
                        with transaction.atomic():
                            listing = Listing.objects.create(
                                landlord=landlord,
                                title=fake.catch_phrase(),
                                description=fake.paragraph(nb_sentences=4),
                                city=random.choice(cities),
                                district=fake.city_suffix(),
                                street_address=fake.street_address(),
                                price=random.randint(400, 2500),
                                rooms=random.randint(1, 5),
                                property_type=random.choice(PropertyType.values),
                                is_active=random.choice([True, True, True, False]),  # mostly active
                            )
                        listings.append(listing)
                        break
                    except IntegrityError:
                        if attempt == max_attempts - 1:
                            self.stdout.write(self.style.WARNING(
                                f'Skipped a listing for {landlord.username}: '
                                f'could not find a free address after {max_attempts} attempts.'
                            ))
        return listings

    # --- bookings -----------------------------------------------------------------

    def _create_bookings(self, listings, tenants):
        """Creates bookings directly via the ORM, bypassing BookingSerializer.
        validate() entirely — so, unlike real API-created bookings, these can
        freely fall outside the min/max advance-notice window or even be in
        the past. That's intentional here: it gives seeded data a realistic
        spread of past/future/pending/confirmed bookings for demoing filters
        and the reviews flow, which all need some already-completed bookings
        to work with.
        """
        bookings = []
        statuses = [Status.PENDING, Status.CONFIRMED, Status.REJECTED, Status.CANCELLED]
        if not listings or not tenants:
            return bookings

        sample_size = min(len(listings), max(1, len(listings) * 2 // 3))
        for listing in random.sample(listings, k=sample_size):
            tenant = random.choice(tenants)
            days_offset = random.randint(-60, 60)
            start_date = timezone.now().date() + timedelta(days=days_offset)
            end_date = start_date + timedelta(days=random.randint(3, 14))
            booking = Booking.objects.create(
                listing=listing,
                tenant=tenant,
                start_date=start_date,
                end_date=end_date,
                status=random.choice(statuses),
            )
            bookings.append(booking)
        return bookings

    # --- reviews --------------------------------------------------------------

    def _create_reviews(self, bookings):
        past_confirmed = [
            b for b in bookings
            if b.status == Status.CONFIRMED and b.end_date < timezone.now().date()
        ]
        for booking in past_confirmed:
            if random.random() < 0.7:  # not every eligible booking gets reviewed
                Review.objects.create(
                    booking=booking,
                    rating=random.randint(1, 5),
                    comment=fake.sentence(nb_words=12),
                )

    # --- statistics -----------------------------------------------------------

    def _create_view_history(self, listings, tenants):
        if not tenants:
            return
        for listing in listings:
            viewers = random.sample(tenants, k=random.randint(0, len(tenants)))
            for viewer in viewers:
                ViewHistory.objects.get_or_create(listing=listing, user=viewer)
            for _ in range(random.randint(0, 5)):  # anonymous views
                ViewHistory.objects.create(listing=listing, user=None)

    def _create_search_queries(self):
        terms = ['berlin', 'balcony', 'cheap apartment', 'studio', 'munich', 'garden', 'pet friendly']
        for term in terms:
            for _ in range(random.randint(1, 8)):
                SearchQuery.objects.create(query_text=term)

