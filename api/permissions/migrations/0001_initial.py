# Generated by Django 2.2.10 on 2020-02-20 00:24

from django.db import migrations, models

from environments.permissions.constants import ENVIRONMENT_PERMISSIONS
from permissions.models import PROJECT_PERMISSION_TYPE, ENVIRONMENT_PERMISSION_TYPE
from projects.permissions import PROJECT_PERMISSIONS


def insert_default_project_permissions(apps, schema_model):
    PermissionModel = apps.get_model('permissions', 'PermissionModel')

    project_permissions = [
        PermissionModel(
            key=permission[0],
            description=permission[1],
            type=PROJECT_PERMISSION_TYPE,
        )
        for permission in PROJECT_PERMISSIONS
    ]
    PermissionModel.objects.bulk_create(project_permissions)


def insert_default_environment_permissions(apps, schema_model):
    PermissionModel = apps.get_model('permissions', 'PermissionModel')

    environment_permissions = [
        PermissionModel(
            key=permission[0],
            description=permission[1],
            type=ENVIRONMENT_PERMISSION_TYPE,
        )
        for permission in ENVIRONMENT_PERMISSIONS
    ]
    PermissionModel.objects.bulk_create(environment_permissions)


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='PermissionModel',
            fields=[
                ('key', models.CharField(max_length=100, primary_key=True, serialize=False)),
                ('description', models.TextField()),
                ('type', models.CharField(choices=[('PROJECT', 'Project'), ('ENVIRONMENT', 'Environment')], max_length=100, null=True)),
            ],
        ),
        migrations.RunPython(insert_default_project_permissions, reverse_code=lambda *args: None),
        migrations.RunPython(insert_default_environment_permissions, reverse_code=lambda *args: None),
    ]
