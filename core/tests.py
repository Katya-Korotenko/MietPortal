from unittest.mock import Mock

from django.test import TestCase

from core.permissions import IsOwnerOrReadOnly


class IsOwnerOrReadOnlyTests(TestCase):
    """Tests the permission class in isolation, without going through
    a real API endpoint — just checking the has_object_permission logic.
    """

    def setUp(self):
        self.permission = IsOwnerOrReadOnly()
        self.owner = Mock()
        self.other_user = Mock()

    def make_request(self, method, user):
        request = Mock()
        request.method = method
        request.user = user
        return request

    def make_object(self, landlord):
        obj = Mock()
        obj.landlord = landlord
        return obj

    def test_safe_method_allowed_for_anyone(self):
        request = self.make_request('GET', self.other_user)
        obj = self.make_object(landlord=self.owner)
        self.assertTrue(self.permission.has_object_permission(request, None, obj))

    def test_write_method_allowed_for_owner(self):
        request = self.make_request('PATCH', self.owner)
        obj = self.make_object(landlord=self.owner)
        self.assertTrue(self.permission.has_object_permission(request, None, obj))

    def test_write_method_denied_for_non_owner(self):
        request = self.make_request('PATCH', self.other_user)
        obj = self.make_object(landlord=self.owner)
        self.assertFalse(self.permission.has_object_permission(request, None, obj))