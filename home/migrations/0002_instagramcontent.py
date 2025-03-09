# Generated by Django 5.1.5 on 2025-02-21 09:27

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='InstagramContent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.URLField(max_length=500)),
                ('content_type', models.CharField(choices=[('dp', 'Profile Picture'), ('post', 'Post'), ('reel', 'Reel'), ('story', 'Story')], max_length=10)),
                ('file', models.FileField(blank=True, null=True, upload_to='instagram_downloads/')),
                ('downloaded_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
