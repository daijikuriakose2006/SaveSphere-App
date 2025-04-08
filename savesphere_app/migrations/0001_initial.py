# Generated by Django 5.0.3 on 2025-04-07 16:41

import django.db.models.deletion
import savesphere_app.models
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Album',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.CharField(default=savesphere_app.models.get_default_user_id, max_length=255)),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('is_public', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('user_id', models.CharField(max_length=255, primary_key=True, serialize=False, unique=True)),
                ('email', models.EmailField(default='default@example.com', max_length=254, unique=True)),
                ('bio', models.TextField(blank=True, max_length=500)),
                ('profile_picture', models.ImageField(blank=True, null=True, upload_to='profile_pics/')),
                ('storage_quota', models.BigIntegerField(default=104857600)),
                ('storage_used', models.BigIntegerField(default=0)),
                ('is_blocked_upload', models.BooleanField(default=False)),
                ('role', models.CharField(choices=[('user', 'Regular User'), ('staff', 'Staff'), ('admin', 'Administrator')], default='user', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Media',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.CharField(default=savesphere_app.models.get_default_user_id, max_length=255)),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('media_type', models.CharField(choices=[('photo', 'Photo'), ('video', 'Video')], max_length=5)),
                ('file', models.FileField(upload_to=savesphere_app.models.user_directory_path)),
                ('thumbnail', models.ImageField(blank=True, null=True, upload_to='thumbnails/')),
                ('is_public', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('album', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='media', to='savesphere_app.album')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Favorite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.CharField(default=savesphere_app.models.get_default_user_id, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('media', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorited_by', to='savesphere_app.media')),
            ],
            options={
                'ordering': ['-created_at'],
                'unique_together': {('user_id', 'media')},
            },
        ),
    ]
