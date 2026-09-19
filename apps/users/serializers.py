from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from core.constants import LANDLORD_GROUP, TENANT_GROUP

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """Handles user registration. Accepts a write-only `role` field (not a
    model field) used only to assign the new user to the matching Tenant/
    Landlord group; the role itself is never stored directly on the user.
    """
    email = serializers.EmailField(
        validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                message='Email already in use.',
            )
        ]
    )
    password = serializers.CharField(write_only=True, validators=[validate_password])
    role = serializers.ChoiceField(choices=['tenant', 'landlord'], write_only=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'first_name', 'last_name', 'phone_number', 'role')

    @transaction.atomic
    def create(self, validated_data):
        """Creates the user with a hashed password, then adds them to the
        Tenant or Landlord group based on `role`. Wrapped in a transaction so
        a failure partway through never leaves a user without a role.
        """
        role = validated_data.pop('role')
        password = validated_data.pop('password')

        user = User(**validated_data)
        user.set_password(password)
        user.save()

        group_name = LANDLORD_GROUP if role == 'landlord' else TENANT_GROUP
        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)

        return user



class UserSerializer(serializers.ModelSerializer):
    """Used by /me/ for both reading and updating the current user's profile.
    username/email/role are read-only — identity fields can't be changed
    through this endpoint, only first_name/last_name/phone_number can.
    """
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'phone_number', 'role')
        read_only_fields = ('id', 'username', 'email', 'role')

    def get_role(self, obj):
        """Derives a single role label from group membership, defaulting to
        'tenant' if the user isn't in the Landlord group."""
        if obj.is_landlord:
            return 'landlord'
        return 'tenant'