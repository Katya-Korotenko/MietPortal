from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.test import APITestCase

from core.constants import TENANT_GROUP, LANDLORD_GROUP

User = get_user_model()


class RegistrationTests(APITestCase):
    """Tests for user registration and role assignment."""

    def setUp(self):
        Group.objects.get_or_create(name=TENANT_GROUP)
        Group.objects.get_or_create(name=LANDLORD_GROUP)

    def registration_payload(self, **overrides):
        payload = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'StrongPass123',
            'first_name': 'John',
            'last_name': 'Doe',
            'phone_number': '+491701234567',
            'role': 'tenant',
        }
        payload.update(overrides)
        return payload

    def test_can_register_as_tenant(self):
        response = self.client.post('/api/users/register/', self.registration_payload())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email='newuser@example.com')
        self.assertTrue(user.is_tenant)
        self.assertFalse(user.is_landlord)

    def test_can_register_as_landlord(self):
        response = self.client.post('/api/users/register/', self.registration_payload(
            username='newlandlord', email='newlandlord@example.com', role='landlord'
        ))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email='newlandlord@example.com')
        self.assertTrue(user.is_landlord)
        self.assertFalse(user.is_tenant)

    def test_password_is_hashed_not_plaintext(self):
        self.client.post('/api/users/register/', self.registration_payload())
        user = User.objects.get(email='newuser@example.com')
        self.assertNotEqual(user.password, 'StrongPass123')
        self.assertTrue(user.check_password('StrongPass123'))

    def test_cannot_register_with_duplicate_email(self):
        self.client.post('/api/users/register/', self.registration_payload())
        response = self.client.post('/api/users/register/', self.registration_payload(username='another'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_register_with_weak_password(self):
        response = self.client.post('/api/users/register/', self.registration_payload(password='123'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_register_with_invalid_role(self):
        response = self.client.post('/api/users/register/', self.registration_payload(role='admin'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_register_with_phone_containing_letters(self):
        response = self.client.post('/api/users/register/', self.registration_payload(
            username='user2', email='user2@example.com', phone_number='+4917abc4567'
        ))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_register_with_too_short_phone(self):
        response = self.client.post('/api/users/register/', self.registration_payload(
            username='user3', email='user3@example.com', phone_number='123'
        ))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_can_register_with_empty_phone(self):
        payload = self.registration_payload(
            username='nophonenuser', email='nophonenuser@example.com'
        )
        payload.pop('phone_number')
        response = self.client.post('/api/users/register/', payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_can_register_with_blank_phone_string(self):
        response = self.client.post('/api/users/register/', self.registration_payload(
            username='blankphoneuser', email='blankphoneuser@example.com', phone_number=''
        ))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class LoginAndProfileTests(APITestCase):
    """Tests for login (by email) and the /me/ endpoint."""

    def setUp(self):
        Group.objects.get_or_create(name=TENANT_GROUP)
        self.user = User.objects.create_user(
            username='janedoe', email='jane@example.com', password='StrongPass123'
        )

    def test_can_login_with_email(self):
        response = self.client.post('/api/users/login/', {
            'email': 'jane@example.com',
            'password': 'StrongPass123',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_cannot_login_with_wrong_password(self):
        response = self.client.post('/api/users/login/', {
            'email': 'jane@example.com',
            'password': 'WrongPass',
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_requires_authentication(self):
        response = self.client.get('/api/users/me/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_own_data(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/users/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'jane@example.com')
        self.assertEqual(response.data['role'], 'tenant')

class LogoutTests(APITestCase):
    """Tests for logout and refresh token blacklisting."""

    def setUp(self):
        Group.objects.get_or_create(name=TENANT_GROUP)
        self.user = User.objects.create_user(
            username='janedoe', email='jane@example.com', password='StrongPass123'
        )

    def get_tokens(self):
        response = self.client.post('/api/users/login/', {
            'email': 'jane@example.com',
            'password': 'StrongPass123',
        })
        return response.data['access'], response.data['refresh']

    def test_logout_blacklists_refresh_token(self):
        access, refresh = self.get_tokens()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

        response = self.client.post('/api/users/logout/', {'refresh': refresh})
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)

        refresh_response = self.client.post('/api/users/login/refresh/', {'refresh': refresh})
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_requires_authentication(self):
        response = self.client.post('/api/users/logout/', {'refresh': 'sometoken'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_without_refresh_token_returns_400(self):
        access, _ = self.get_tokens()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        response = self.client.post('/api/users/logout/', {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_with_invalid_token_returns_400(self):
        access, _ = self.get_tokens()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        response = self.client.post('/api/users/logout/', {'refresh': 'invalid-token'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_blacklist_same_token_twice(self):
        access, refresh = self.get_tokens()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        self.client.post('/api/users/logout/', {'refresh': refresh})

        response = self.client.post('/api/users/logout/', {'refresh': refresh})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MeUpdateTests(APITestCase):
    """Tests for updating own profile via /me/."""

    def setUp(self):
        Group.objects.get_or_create(name=TENANT_GROUP)
        self.user = User.objects.create_user(
            username='janedoe', email='jane@example.com', password='StrongPass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_can_update_first_name_and_phone(self):
        response = self.client.patch('/api/users/me/', {
            'first_name': 'Jane',
            'phone_number': '+491701234567',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Jane')

    def test_cannot_update_username_or_email_via_me(self):
        response = self.client.patch('/api/users/me/', {
            'username': 'hacked_username',
            'email': 'hacked@example.com',
            'first_name': 'Jane',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'janedoe')
        self.assertEqual(self.user.email, 'jane@example.com')
        self.assertEqual(self.user.first_name, 'Jane')

