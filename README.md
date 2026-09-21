# MietPortal — Rental Housing Platform Backend

🇷🇺 [Русская версия](README.ru.md)

A Django + Django REST Framework backend for a rental housing platform:
listings, search and filtering, bookings, reviews, and popularity
statistics — with a "tenant / landlord" role model.

## Tech Stack

- **Django** + **Django REST Framework** — API
- **MySQL** (engine is set via `DB_ENGINE` in `.env` — switching to
  PostgreSQL/SQLite requires no code changes)
- **SimpleJWT** — token-based authentication, with a blacklist for logout
- **django-filter** — listing filtering
- **drf-spectacular** — API auto-documentation (Swagger UI)
- **django-simple-history** — booking change history
- **WhiteNoise** — serves static files without a separate web server
- **Docker / docker-compose** — containerization and local runs
- **Faker** — test data generation for development

## Project Structure

```
MietPortal/
├── manage.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── dockerignore
├── .env.example
│
├── config/                      # Django project settings
│   ├── settings.py                  # DB_ENGINE, JWT, DRF, installed apps
│   ├── urls.py
│   ├── wsgi.py / asgi.py
│
├── core/                        # shared infrastructure for all apps
│   ├── models.py                    # UniqueID (UUID pk), TimeStampedModel, SoftDeleteModel
│   ├── choices.py                   # PropertyType, Status
│   ├── constants.py                  # roles, date limits, currency, phone regex
│   ├── permissions.py                # IsLandlord, IsTenant, IsOwnerOrReadOnly
│   ├── tests.py
│   └── management/commands/
│       └── seed_data.py               # populates the local DB with test data
│
├── apps/
│   ├── users/                    # custom User (role via Group), JWT auth
│   │   ├── migrations/                # incl. 0002_create_groups — creates Tenant/Landlord
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py                  # UserBasic — login by email, UUID id
│   │   ├── serializers.py             # registration with role assignment, /me/ profile
│   │   ├── tests.py
│   │   ├── urls.py
│   │   └── views.py                   # RegisterView, LogoutView (blacklist), MeView
│   │
│   ├── listings/                 # listings — the core of the app
│   │   ├── migrations/
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── filters.py                 # filtering by price/rooms/city/type
│   │   ├── models.py                  # Listing (soft delete, unique constraint on address)
│   │   ├── serializers.py
│   │   ├── tests.py
│   │   ├── urls.py
│   │   └── views.py                   # CRUD + view/search logging
│   │
│   ├── bookings/                  # bookings
│   │   ├── migrations/
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py                  # Booking (history via simple_history)
│   │   ├── permissions.py             # IsBookingTenant, IsBookingLandlord
│   │   ├── serializers.py             # date, overlap, and deadline validation
│   │   ├── tests.py
│   │   ├── urls.py
│   │   └── views.py                   # confirm / reject / cancel as separate actions
│   │
│   ├── reviews/                   # reviews and ratings
│   │   ├── migrations/
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py                   # Review (one review per booking)
│   │   ├── permissions.py              # IsReviewOwner
│   │   ├── serializers.py              # review eligibility only after a completed stay
│   │   ├── tests.py
│   │   ├── urls.py
│   │   └── views.py
│   │
│   └── statistic/                  # search/view history, popularity rankings
│       ├── migrations/
│       ├── admin.py
│       ├── apps.py
│       ├── models.py                    # SearchQuery, ViewHistory
│       ├── tests.py
│       ├── urls.py
│       └── views.py                     # popular_searches, popular_listings
│
└── staticfiles/                   # collected static files (Django admin, DRF browsable API)
```

Every app follows the standard Django-app layout: `admin.py`, `apps.py`,
`models.py`, `tests.py`, `urls.py`, `views.py`, and `migrations/` exist
**everywhere** — this is not optional, it's the guaranteed minimum for any
app with a model. The targeted additions are: `serializers.py`, present in
every app except `statistic` (there, both endpoints return aggregated data
directly via `Response()` / reuse `ListingSerializer` from `listings`
rather than defining their own serialization model); `permissions.py` —
wherever custom permission logic is needed (`bookings`, `reviews`, `core`);
`filters.py` — only in `listings`.

## Roles and Permissions

The user's role (tenant/landlord) is implemented through Django's built-in
`Group` mechanism rather than a dedicated field — this gives ready-made
integration with the Django admin permission system. The `Tenant`/`Landlord`
groups are created automatically by the
`apps/users/migrations/0002_create_groups.py` migration. The
`is_tenant`/`is_landlord` properties on the `User` model hide the
implementation details.

| Action | Tenant | Landlord |
|---|---|---|
| View and search listings | ✅ | ✅ |
| Create/edit listings | ❌ | ✅ (own listings only) |
| Book a listing | ✅ | ❌ |
| Confirm/reject a booking | ❌ | ✅ (on own listings only) |
| Cancel a booking | ✅ (own bookings only, 7+ days ahead) | ❌ |
| Leave a review | ✅ (after a completed stay) | — |

## Implementation Notes

- **Soft delete** — deleting a listing doesn't erase the data, it flags
  `is_deleted=True`, preserving the history of related bookings/reviews.
  A real, permanent deletion is available via `hard_delete()`.
- **UUID instead of a numeric id** — used for users, so identifiers aren't
  sequentially guessable.
- **Conditional unique constraints** — a listing's address is unique only
  among non-deleted records, allowing the same address to be re-listed
  after the old listing is deleted.
- **JWT logout via blacklist** — access tokens can't be revoked directly,
  so logout invalidates the refresh token through
  `rest_framework_simplejwt.token_blacklist`.
- **Universal `DB_ENGINE`** — the database engine is set via an
  environment variable, with no `if/else` branching in `settings.py`; any
  engine works as long as the matching driver is installed.

> **Known limitation:** MySQL does not support conditional (partial)
> unique indexes (`UniqueConstraint(condition=Q(...))`). Django detects
> this and skips creating the constraint at the database level (see the
> `models.W036` warning during `migrate`), for both the listing-address
> uniqueness rule and the view-history deduplication rule. Both rules are
> still enforced at the application level — through `ListingSerializer.
> validate()` for listings, and through `get_or_create()` for view
> history — so the business rule holds for every request made through the
> API. What's missing is the extra safety net a DB-level constraint would
> provide against writes that bypass the API entirely (e.g. direct ORM
> access or the Django admin). This is a deliberate trade-off driven by
> the requirement to use MySQL as the primary database.

## Quick Start (local, without Docker)

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env  # fill in the variables

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Running with Docker

```bash
cp .env.example .env
docker compose up --build
```

This brings up three services:
- **db** — MySQL
- **web** — Django + gunicorn (migrations and `collectstatic` run
  automatically on startup)
- **scheduler** — clears expired JWT tokens once a week
  (`flushexpiredtokens`)

The app is available at `http://localhost:8000/`, and the API docs at
`http://localhost:8000/api/docs/`.

## Seeding Test Data

For local development and demos, a management command generates a
realistic dataset (users, listings, bookings, reviews, view/search
history) using `Faker`:

```bash
python manage.py seed_data --flush
```

Options:
- `--landlords N` — number of landlords (default 5)
- `--tenants N` — number of tenants (default 10)
- `--listings-per-landlord N` — listings per landlord (default 3)
- `--flush` — delete previously seeded data before creating new data

All generated users have the password `TestPass123`, with emails like
`landlord0@example.com` / `tenant0@example.com`.

> Data is created directly through the ORM, bypassing
> `BookingSerializer`'s business validation — this is intentional, to get
> a realistic spread of past/future bookings with different statuses for
> demoing filters and the review flow.

## Tests

```bash
python manage.py test
```

Tests cover every app: role-based permissions, business-rule validation
(booking date overlaps, deadlines, listing uniqueness), soft/hard delete,
JWT authentication and blacklisting, and automatic view/search statistics
collection.

## Main Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/users/register/` | Registration (role: tenant/landlord) |
| POST | `/api/users/login/` | Get a JWT token (by email) |
| POST | `/api/users/login/refresh/` | Refresh the access token |
| POST | `/api/users/logout/` | Logout (blacklists the refresh token) |
| GET/PATCH | `/api/users/me/` | Current user's profile |
| GET/POST | `/api/listings/` | List listings / create one (landlord) |
| GET/PATCH/DELETE | `/api/listings/{id}/` | A single listing |
| GET/POST | `/api/bookings/` | The user's bookings |
| POST | `/api/bookings/{id}/confirm/` | Confirm (landlord) |
| POST | `/api/bookings/{id}/reject/` | Reject (landlord) |
| POST | `/api/bookings/{id}/cancel/` | Cancel (tenant, 7+ days ahead) |
| GET/POST | `/api/reviews/?listing={id}` | Reviews for a listing |
| GET | `/api/statistic/popular_searches/` | Top search queries |
| GET | `/api/statistic/popular_listings/` | Top listings by views |

Listing filters: `?city=&district=&property_type=&min_price=&max_price=&min_rooms=&max_rooms=`,
search: `?search=keyword`, ordering: `?ordering=price` / `-created_at`.