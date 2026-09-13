from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

from core.models import UniqueID
from core.constants import LANDLORD_GROUP, TENANT_GROUP, PHONE_REGEX


class UserBasic(UniqueID, AbstractUser):
    phone_number = models.CharField(max_length=20,
                                    blank=True,
                                    validators=[RegexValidator(
                                        regex=PHONE_REGEX,
                                        message='Enter a valid phone number.')],
                                    )
    email = models.EmailField(unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['username']

    def __str__(self):
        return self.username

    @property
    def is_landlord(self):
        return self.groups.filter(name=LANDLORD_GROUP).exists()

    @property
    def is_tenant(self):
        return self.groups.filter(name=TENANT_GROUP).exists()