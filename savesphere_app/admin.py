from django.contrib import admin
from .models import UserProfile, Album, Media, Favorite

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('email', 'user_id', 'storage_quota', 'storage_used', 'is_blocked_upload')
    list_filter = ('is_blocked_upload',)
    search_fields = ('email', 'user_id')

@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ('name', 'user_id', 'is_public', 'created_at')
    list_filter = ('is_public', 'created_at')
    search_fields = ('name', 'user_id')

@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ('title', 'user_id', 'media_type', 'is_public', 'created_at')
    list_filter = ('media_type', 'is_public', 'created_at')
    search_fields = ('title', 'user_id')

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'media', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user_id', 'media__title')
