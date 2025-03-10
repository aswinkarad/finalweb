# Generated by Django 5.1.5 on 2025-02-21 10:26

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0003_remove_instagramcontent_file'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SocialMediaContent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('platform', models.CharField(choices=[('instagram', 'Instagram'), ('twitter', 'Twitter'), ('facebook', 'Facebook')], max_length=20)),
                ('url', models.URLField(max_length=500)),
                ('content_type', models.CharField(choices=[('dp', 'Profile Picture'), ('post', 'Post'), ('reel', 'Reel'), ('story', 'Story'), ('video', 'Video'), ('image', 'Image')], max_length=20)),
                ('downloaded_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-downloaded_at'],
            },
        ),
        migrations.DeleteModel(
            name='InstagramContent',
        ),
    ]
