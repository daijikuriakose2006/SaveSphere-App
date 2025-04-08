from django.db import models
from django.utils import timezone
import os
import uuid

def user_directory_path(instance, filename):
    # File will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return f'user_{instance.user_id}/{filename}'

def get_default_user_id():
    # This is a fallback for existing data
    return 'default_user'

class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('user', 'Regular User'),
        ('staff', 'Staff'),
        ('admin', 'Administrator'),
    )
    
    user_id = models.CharField(max_length=255, unique=True, primary_key=True)  # Supabase user ID
    email = models.EmailField(unique=True, default='default@example.com')
    bio = models.TextField(max_length=500, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    storage_quota = models.BigIntegerField(default=104857600)  # 100MB in bytes
    storage_used = models.BigIntegerField(default=0)
    is_blocked_upload = models.BooleanField(default=False)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.email}'s Profile"

    def get_storage_used_mb(self):
        return round(self.storage_used / (1024 * 1024), 2)

    def get_storage_quota_mb(self):
        return round(self.storage_quota / (1024 * 1024), 2)

    def get_storage_percentage(self):
        if self.storage_quota > 0:
            return (self.storage_used / self.storage_quota) * 100
        return 100

class Album(models.Model):
    user_id = models.CharField(max_length=255, default=get_default_user_id)  # Supabase user ID
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.user_id}"

    class Meta:
        ordering = ['-created_at']

class Media(models.Model):
    MEDIA_TYPES = (
        ('photo', 'Photo'),
        ('video', 'Video'),
    )

    user_id = models.CharField(max_length=255, default=get_default_user_id)  # Supabase user ID
    album = models.ForeignKey(Album, on_delete=models.CASCADE, null=True, blank=True, related_name='media')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    media_type = models.CharField(max_length=5, choices=MEDIA_TYPES)
    file = models.FileField(upload_to=user_directory_path)
    thumbnail = models.ImageField(upload_to='thumbnails/', null=True, blank=True)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.user_id}"

    def delete(self, *args, **kwargs):
        # Delete the file when the media object is deleted
        if self.file:
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        if self.thumbnail:
            if os.path.isfile(self.thumbnail.path):
                os.remove(self.thumbnail.path)
        super().delete(*args, **kwargs)

    class Meta:
        ordering = ['-created_at']

class Favorite(models.Model):
    user_id = models.CharField(max_length=255, default=get_default_user_id)  # Supabase user ID
    media = models.ForeignKey(Media, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user_id', 'media')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user_id}'s favorite: {self.media.title}" 