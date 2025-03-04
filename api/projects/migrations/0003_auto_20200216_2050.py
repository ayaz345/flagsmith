# Generated by Django 2.2.10 on 2020-02-16 20:50

from django.db import migrations

from projects.permissions import PROJECT_PERMISSIONS


def insert_default_permissions(apps, schema_model):
    ProjectPermission = apps.get_model('projects', 'ProjectPermission')

    project_permissions = [
        ProjectPermission(key=permission[0], description=permission[1])
        for permission in PROJECT_PERMISSIONS
    ]
    ProjectPermission.objects.bulk_create(project_permissions)


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0002_projectpermission_userpermissiongroupprojectpermission_userprojectpermission'),
    ]

    operations = [
        migrations.RunPython(insert_default_permissions, reverse_code=lambda *args: None)
    ]
