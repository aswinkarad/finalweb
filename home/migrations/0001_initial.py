# Generated by Django 5.1.6 on 2025-02-08 21:11

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
            ],
            options={
                'verbose_name_plural': 'Categories',
            },
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('image', models.ImageField(blank=True, null=True, upload_to='projects/')),
                ('link', models.URLField(blank=True)),
                ('icon', models.CharField(choices=[('fab fa-python', 'Python'), ('fab fa-js', 'JavaScript'), ('fab fa-react', 'React'), ('fab fa-angular', 'Angular'), ('fab fa-vue', 'Vue.js'), ('fab fa-node', 'Node.js'), ('fab fa-php', 'PHP'), ('fab fa-java', 'Java'), ('fab fa-html5', 'HTML5'), ('fab fa-css3', 'CSS3'), ('fab fa-sass', 'Sass'), ('fab fa-less', 'Less'), ('fab fa-wordpress', 'WordPress'), ('fab fa-laravel', 'Laravel'), ('fab fa-django', 'Django'), ('fab fa-docker', 'Docker'), ('fab fa-aws', 'AWS'), ('fab fa-github', 'GitHub'), ('fab fa-gitlab', 'GitLab'), ('fab fa-bitbucket', 'Bitbucket'), ('fas fa-database', 'Database'), ('fas fa-server', 'Server'), ('fas fa-code', 'Code'), ('fas fa-mobile-alt', 'Mobile'), ('fas fa-desktop', 'Desktop')], default='fab fa-python', help_text='Select a Font Awesome icon for your project', max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('sub_heading', models.CharField(max_length=200)),
                ('notes', models.TextField()),
                ('image', models.ImageField(blank=True, null=True, upload_to='posts/')),
                ('link', models.URLField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='posts', to='home.category')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='home.post')),
            ],
        ),
        migrations.CreateModel(
            name='Rating',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stars', models.IntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ratings', to='home.post')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('post', 'user')},
            },
        ),
    ]
