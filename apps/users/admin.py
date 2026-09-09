from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import UserBasic


@admin.register(UserBasic)
class CustomUserAdmin(UserAdmin):
    search_fields = ('username', 'email')
    list_display = ('username', 'email', 'is_staff', 'is_active', 'get_groups')

    def get_groups(self, obj):
        return ", ".join([g.name for g in obj.groups.all()])

    get_groups.short_description = 'Groups'