# Generated by Django 5.1.5 on 2025-02-21 09:31

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0002_instagramcontent'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='instagramcontent',
            name='file',
        ),
    ]
