from django.db import migrations

from core.constants import TENANT_GROUP, LANDLORD_GROUP


def create_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.get_or_create(name=TENANT_GROUP)
    Group.objects.get_or_create(name=LANDLORD_GROUP)


def remove_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name__in=[TENANT_GROUP, LANDLORD_GROUP]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0001_initial'),
    ]
    operations = [
        migrations.RunPython(create_groups, remove_groups),
    ]