from django.contrib.auth.models import AbstractUser
from django.db import models

from core.models import UniqueID
from core.constants import LANDLORD_GROUP, TENANT_GROUP


class UserBasic(UniqueID, AbstractUser):
    phone_number = models.CharField(max_length=20, blank=True)
    email = models.EmailField(unique=True)
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.username

    @property
    def is_landlord(self):
        return self.groups.filter(name=LANDLORD_GROUP).exists()

    @property
    def is_tenant(self):
        return self.groups.filter(name=TENANT_GROUP).exists()