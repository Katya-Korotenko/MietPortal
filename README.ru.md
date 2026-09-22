# MietPortal — Backend для системы аренды жилья

🇬🇧 [English version](README.md)

Backend-приложение на Django + Django REST Framework для платформы аренды
жилья: объявления, поиск и фильтрация, бронирование, отзывы, статистика
популярности — с ролевой моделью «арендатор / арендодатель».

## Стек технологий

- **Django** + **Django REST Framework** — API
- **MySQL** (движок задаётся через `DB_ENGINE` в `.env` — без правки кода
  можно переключиться на PostgreSQL/SQLite)
- **SimpleJWT** — аутентификация по токенам, с blacklist для logout
- **django-filter** — фильтрация объявлений
- **drf-spectacular** — генерация схемы API
- **django-simple-history** — история изменений бронирований
- **WhiteNoise** — раздача статики без отдельного веб-сервера
- **Docker / docker-compose** — контейнеризация и локальный запуск
- **Faker** — генерация тестовых данных для разработки

## Структура проекта

```
MietPortal/
├── manage.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── dockerignore
├── .env.example
│
├── config/                      # настройки Django-проекта
│   ├── settings.py                  # DB_ENGINE, JWT, DRF, приложения
│   ├── urls.py
│   ├── wsgi.py / asgi.py
│
├── core/                        # общая инфраструктура для всех apps
│   ├── models.py                    # UniqueID (UUID pk), TimeStampedModel, SoftDeleteModel
│   ├── choices.py                   # PropertyType, Status
│   ├── constants.py                  # роли, лимиты по датам, валюта, regex телефона
│   ├── permissions.py                # IsLandlord, IsTenant, IsOwnerOrReadOnly
│   ├── tests.py
│   └── management/commands/
│       └── seed_data.py               # наполнение локальной БД тестовыми данными
│
├── apps/
│   ├── users/                    # кастомный User (роль через Group), JWT-аутентификация
│   │   ├── migrations/                # включая 0002_create_groups — создаёт Tenant/Landlord
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py                  # UserBasic — вход по email, UUID id
│   │   ├── serializers.py             # регистрация с назначением роли, профиль /me/
│   │   ├── tests.py
│   │   ├── urls.py
│   │   └── views.py                   # RegisterView, LogoutView (blacklist), MeView
│   │
│   ├── listings/                 # объявления — ядро приложения
│   │   ├── migrations/
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── filters.py                 # фильтрация по цене/комнатам/городу/типу
│   │   ├── models.py                  # Listing (soft delete, unique constraint по адресу)
│   │   ├── serializers.py
│   │   ├── tests.py
│   │   ├── urls.py
│   │   └── views.py                   # CRUD + логирование просмотров/поиска
│   │
│   ├── bookings/                  # бронирование
│   │   ├── migrations/
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py                  # Booking (история через simple_history)
│   │   ├── permissions.py             # IsBookingTenant, IsBookingLandlord
│   │   ├── serializers.py             # валидация дат, пересечений, сроков
│   │   ├── tests.py
│   │   ├── urls.py
│   │   └── views.py                   # confirm / reject / cancel как отдельные actions
│   │
│   ├── reviews/                   # отзывы и рейтинги
│   │   ├── migrations/
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py                   # Review (один отзыв на бронирование)
│   │   ├── permissions.py              # IsReviewOwner
│   │   ├── serializers.py              # право на отзыв только после завершённой аренды
│   │   ├── tests.py
│   │   ├── urls.py
│   │   └── views.py
│   │
│   └── statistic/                  # история поиска и просмотров, топ по популярности
│       ├── migrations/
│       ├── admin.py
│       ├── apps.py
│       ├── models.py                    # SearchQuery, ViewHistory
│       ├── tests.py
│       ├── urls.py
│       └── views.py                     # popular_searches, popular_listings
│
└── staticfiles/                   # собранная статика (Django admin, DRF browsable API)
```

Каждое приложение — стандартный Django-app: `admin.py`, `apps.py`,
`models.py`, `tests.py`, `urls.py`, `views.py` и `migrations/` есть
**везде**, это не опция, а гарантированный минимум для любого приложения
с моделью. Точечные дополнения — `serializers.py` есть во всех, кроме
`statistic` (там оба эндпоинта отдают агрегированные данные напрямую через
`Response()`/переиспользуют `ListingSerializer` из `listings`, а не
описывают свою модель для сериализации); `permissions.py` — там, где нужна
своя логика прав (`bookings`, `reviews`, `core`); `filters.py` — только в
`listings`.

## Роли и права доступа

Роль пользователя (арендатор/арендодатель) реализована через встроенный
механизм Django `Group`, а не через отдельное поле — это даёт готовую
интеграцию с системой прав Django admin. Группы `Tenant`/`Landlord`
создаются автоматически миграцией `apps/users/migrations/0002_create_groups.py`.
Свойства `is_tenant`/`is_landlord` на модели `User` скрывают детали
реализации.

| Действие | Арендатор | Арендодатель |
|---|---|---|
| Просмотр и поиск объявлений | ✅ | ✅ |
| Создание/редактирование объявлений | ❌ | ✅ (только свои) |
| Бронирование | ✅ | ❌ |
| Подтверждение/отклонение брони | ❌ | ✅ (только на свои объявления) |
| Отмена брони | ✅ (только своей, за 7+ дней) | ❌ |
| Отзыв на жильё | ✅ (после завершённой аренды) | — |

## Особенности реализации

- **Soft delete** — удаление объявлений не стирает данные, а помечает
  `is_deleted=True`, сохраняя историю бронирований/отзывов. Жёсткое удаление
  доступно через `hard_delete()`.
- **UUID вместо числового id** — у пользователей, чтобы идентификаторы не
  были последовательно угадываемыми.
- **Условная уникальность без partial-индексов** — MySQL не поддерживает
  условные (частичные) `UniqueConstraint(condition=Q(...))`. Вместо этого
  `Listing` использует `GeneratedField` (`active_key`), которое база
  вычисляет сама: `1` для неудалённых записей, `NULL` для удалённых. Так
  как `NULL` никогда не конфликтует в уникальном индексе, обычный
  `UniqueConstraint` на `(landlord, city, street_address, active_key)`
  ведёт себя точно как условный — ограничение соблюдает сама MySQL, а не
  только уровень приложения. `ListingSerializer.validate()` всё равно
  дублирует проверку, чтобы вернуть аккуратный `400` вместо сырого
  `IntegrityError`; гонку, проскочившую мимо валидации, ловит
  `_save_or_400()` во вьюхе. Для `ViewHistory` такой обходной путь не
  понадобился: `NULL` по умолчанию никогда не конфликтует в SQL, поэтому
  обычный `UniqueConstraint` на `(listing, user)` уже дедуплицирует
  просмотры авторизованных пользователей, оставляя анонимные (`user=NULL`)
  без ограничений.
- **Посуточная модель цены** — `price` объявления — это цена за ночь, что
  соответствует посуточной, а не помесячной аренде. При создании бронирования
  текущая цена объявления сохраняется в `price_per_night` — так более поздние
  изменения цены объявления не влияют на уже созданные брони. Бронирование
  отдаёт вычисляемое поле `total_price` (`price_per_night × количество ночей`).
- **JWT logout через blacklist** — access-токены нельзя отозвать напрямую,
  поэтому logout инвалидирует refresh-токен через
  `rest_framework_simplejwt.token_blacklist`.
- **Универсальный `DB_ENGINE`** — движок базы данных задаётся переменной
  окружения, без веток `if/else` в `settings.py`; поддерживается любой
  движок, для которого установлен соответствующий драйвер.

## Быстрый старт (локально, без Docker)

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env  # заполнить переменные

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Запуск через Docker

```bash
cp .env.example .env
docker compose up --build
```

Поднимаются три сервиса:
- **db** — MySQL
- **web** — Django + gunicorn (миграции и `collectstatic` выполняются
  автоматически при старте)
- **scheduler** — раз в неделю чистит просроченные JWT-токены
  (`flushexpiredtokens`)

Приложение доступно на `http://localhost:8000/`.

## Наполнение базы тестовыми данными

Для локальной разработки и демонстрации есть management-команда, которая
генерирует реалистичный набор данных (пользователей, объявления,
бронирования, отзывы, историю просмотров и поиска) через `Faker`:

```bash
python manage.py seed_data --flush
```

Параметры:
- `--landlords N` — количество арендодателей (по умолчанию 5)
- `--tenants N` — количество арендаторов (по умолчанию 10)
- `--listings-per-landlord N` — объявлений на арендодателя (по умолчанию 3)
- `--flush` — удалить ранее сгенерированные данные перед созданием новых

Все созданные пользователи имеют пароль `TestPass123`, email вида
`landlord0@example.com` / `tenant0@example.com`.

> Данные создаются напрямую через ORM, в обход бизнес-валидации
> `BookingSerializer` — это осознанно, чтобы получить реалистичный разброс
> прошлых/будущих/разных по статусу бронирований для демонстрации фильтров
> и потока отзывов.

## Тесты

```bash
python manage.py test
```

Тестами покрыты все приложения: права доступа по ролям, валидация бизнес-
правил (пересечение дат бронирования, сроки, уникальность объявлений),
soft/hard delete, JWT-аутентификация и blacklist, автоматический сбор
статистики просмотров/поиска.

## Основные эндпоинты

| Метод | Путь | Описание |
|---|---|---|
| POST | `/api/users/register/` | Регистрация (роль: tenant/landlord) |
| POST | `/api/users/login/` | Получение JWT-токена (по email) |
| POST | `/api/users/login/refresh/` | Обновление access-токена |
| POST | `/api/users/logout/` | Logout (blacklist refresh-токена) |
| GET/PATCH | `/api/users/me/` | Профиль текущего пользователя |
| GET/POST | `/api/listings/` | Список объявлений / создание (landlord) |
| GET/PATCH/DELETE | `/api/listings/{id}/` | Объявление |
| GET/POST | `/api/bookings/` | Бронирования пользователя |
| POST | `/api/bookings/{id}/confirm/` | Подтверждение (landlord) |
| POST | `/api/bookings/{id}/reject/` | Отклонение (landlord) |
| POST | `/api/bookings/{id}/cancel/` | Отмена (tenant, за 7+ дней) |
| GET/POST | `/api/reviews/?listing={id}` | Отзывы по объявлению |
| GET | `/api/statistic/popular_searches/` | Топ поисковых запросов |
| GET | `/api/statistic/popular_listings/` | Топ объявлений по просмотрам |

Фильтрация объявлений: `?city=&district=&property_type=&min_price=&max_price=&min_rooms=&max_rooms=`,
поиск: `?search=ключевое слово`, сортировка: `?ordering=price` / `-created_at`.