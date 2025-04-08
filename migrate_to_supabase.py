#!/usr/bin/env python
"""
Migration script to move data from SQLite to Supabase.
"""

import os
import sys
import django
import uuid
from datetime import datetime

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'savesphere.settings')
django.setup()

from django.contrib.auth.models import User
from savesphere_app.models import UserProfile, Album, Media, Favorite
from savesphere.supabase import get_supabase_client
from django.conf import settings

def main():
    """Main migration function."""
    print("Starting migration to Supabase...")
    
    # Get Supabase client
    supabase = get_supabase_client()
    
    if not supabase:
        print("Error: Supabase client not configured. Please check your .env file.")
        sys.exit(1)
    
    # Create storage bucket if it doesn't exist
    try:
        buckets = supabase.storage.list_buckets()
        bucket_names = [bucket['name'] for bucket in buckets]
        
        if settings.SUPABASE_BUCKET not in bucket_names:
            print(f"Creating storage bucket: {settings.SUPABASE_BUCKET}")
            supabase.storage.create_bucket(settings.SUPABASE_BUCKET, {'public': True})
    except Exception as e:
        print(f"Error setting up storage bucket: {str(e)}")
        sys.exit(1)
    
    # Migrate users and profiles
    user_id_map = migrate_users(supabase)
    
    # Migrate albums with new user IDs
    album_id_map = migrate_albums(supabase, user_id_map)
    
    # Migrate media with new user and album IDs
    media_id_map = migrate_media(supabase, user_id_map, album_id_map)
    
    # Migrate favorites with new user and media IDs
    migrate_favorites(supabase, user_id_map, media_id_map)
    
    print("Migration completed successfully!")

def migrate_users(supabase):
    """Migrate users and their profiles."""
    print("Migrating users and profiles...")
    
    user_id_map = {}  # Maps Django user IDs to Supabase user IDs
    
    for user in User.objects.all():
        print(f"Migrating user: {user.username}")
        
        try:
            # Create user in Supabase Auth
            # Note: In a real migration, you'd handle passwords differently
            # This is a simplified approach for demonstration
            password = f"Temp{uuid.uuid4().hex[:8]}"  # Temporary password
            response = supabase.auth.admin.create_user({
                "email": user.email,
                "password": password,
                "email_confirm": True,
                "user_metadata": {
                    "username": user.username,
                    "is_staff": user.is_staff,
                    "is_superuser": user.is_superuser
                }
            })
            
            supabase_user_id = response.user.id
            user_id_map[user.id] = supabase_user_id
            
            # Get user profile
            try:
                profile = UserProfile.objects.get(user=user)
                
                # Upload profile picture if exists
                profile_pic_url = None
                if profile.profile_picture:
                    try:
                        file_path = profile.profile_picture.path
                        storage_path = f"{supabase_user_id}/profile/{os.path.basename(file_path)}"
                        
                        with open(file_path, 'rb') as f:
                            supabase.storage.from_(settings.SUPABASE_BUCKET).upload(
                                storage_path,
                                f.read()
                            )
                        
                        profile_pic_url = supabase.storage.from_(settings.SUPABASE_BUCKET).get_public_url(storage_path)
                    except Exception as e:
                        print(f"  Warning: Could not upload profile picture: {str(e)}")
                
                # Create profile in Supabase
                profile_data = {
                    'id': supabase_user_id,
                    'username': user.username,
                    'bio': profile.bio or '',
                    'profile_picture_url': profile_pic_url,
                    'storage_quota': profile.storage_quota,
                    'storage_used': profile.storage_used,
                    'is_blocked_upload': profile.is_blocked_upload,
                    'created_at': profile.created_at.isoformat() if profile.created_at else datetime.now().isoformat(),
                    'updated_at': profile.updated_at.isoformat() if profile.updated_at else datetime.now().isoformat()
                }
                
                supabase.table('profiles').insert(profile_data).execute()
                print(f"  Profile migrated for: {user.username}")
                
            except UserProfile.DoesNotExist:
                # Create a default profile
                profile_data = {
                    'id': supabase_user_id,
                    'username': user.username,
                    'bio': '',
                    'profile_picture_url': None,
                    'storage_quota': 104857600,  # 100MB
                    'storage_used': 0,
                    'is_blocked_upload': False,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                
                supabase.table('profiles').insert(profile_data).execute()
                print(f"  Default profile created for: {user.username}")
                
        except Exception as e:
            print(f"  Error migrating user {user.username}: {str(e)}")
    
    return user_id_map

def migrate_albums(supabase, user_id_map):
    """Migrate albums."""
    print("Migrating albums...")
    
    album_id_map = {}  # Maps Django album IDs to Supabase album IDs
    
    for album in Album.objects.all():
        print(f"Migrating album: {album.name}")
        
        try:
            # Map the user ID
            supabase_user_id = user_id_map.get(album.user_id)
            if not supabase_user_id:
                print(f"  Warning: Could not find Supabase user ID for Django user ID: {album.user_id}")
                continue
            
            # Create a new UUID for the album
            new_album_id = str(uuid.uuid4())
            album_id_map[album.id] = new_album_id
            
            # Create album in Supabase
            album_data = {
                'id': new_album_id,
                'user_id': supabase_user_id,
                'name': album.name,
                'description': album.description or '',
                'is_public': album.is_public,
                'created_at': album.created_at.isoformat() if album.created_at else datetime.now().isoformat(),
                'updated_at': album.updated_at.isoformat() if album.updated_at else datetime.now().isoformat()
            }
            
            supabase.table('albums').insert(album_data).execute()
            print(f"  Album migrated: {album.name}")
            
        except Exception as e:
            print(f"  Error migrating album {album.name}: {str(e)}")
    
    return album_id_map

def migrate_media(supabase, user_id_map, album_id_map):
    """Migrate media files."""
    print("Migrating media files...")
    
    media_id_map = {}  # Maps Django media IDs to Supabase media IDs
    
    for media in Media.objects.all():
        print(f"Migrating media: {media.title}")
        
        try:
            # Map the user ID
            supabase_user_id = user_id_map.get(media.user_id)
            if not supabase_user_id:
                print(f"  Warning: Could not find Supabase user ID for Django user ID: {media.user_id}")
                continue
            
            # Map the album ID if it exists
            supabase_album_id = None
            if media.album_id:
                supabase_album_id = album_id_map.get(media.album_id)
                if not supabase_album_id:
                    print(f"  Warning: Could not find Supabase album ID for Django album ID: {media.album_id}")
            
            # Create a new UUID for the media
            new_media_id = str(uuid.uuid4())
            media_id_map[media.id] = new_media_id
            
            # Upload media file to Supabase Storage
            file_url = None
            storage_path = None
            file_size = 0
            
            if media.file:
                try:
                    file_path = media.file.path
                    file_name = os.path.basename(file_path)
                    storage_path = f"{supabase_user_id}/{new_media_id}/{file_name}"
                    
                    # Get file size
                    file_size = os.path.getsize(file_path)
                    
                    # Upload file
                    with open(file_path, 'rb') as f:
                        supabase.storage.from_(settings.SUPABASE_BUCKET).upload(
                            storage_path,
                            f.read()
                        )
                    
                    file_url = supabase.storage.from_(settings.SUPABASE_BUCKET).get_public_url(storage_path)
                    print(f"  File uploaded: {file_name}")
                    
                except Exception as e:
                    print(f"  Warning: Could not upload media file: {str(e)}")
            
            # Create media in Supabase
            media_data = {
                'id': new_media_id,
                'user_id': supabase_user_id,
                'album_id': supabase_album_id,
                'title': media.title,
                'description': media.description or '',
                'media_type': media.media_type,
                'file_url': file_url,
                'file_size': file_size,
                'storage_path': storage_path,
                'is_public': media.is_public,
                'created_at': media.created_at.isoformat() if media.created_at else datetime.now().isoformat(),
                'updated_at': media.updated_at.isoformat() if media.updated_at else datetime.now().isoformat()
            }
            
            supabase.table('media').insert(media_data).execute()
            print(f"  Media record migrated: {media.title}")
            
        except Exception as e:
            print(f"  Error migrating media {media.title}: {str(e)}")
    
    return media_id_map

def migrate_favorites(supabase, user_id_map, media_id_map):
    """Migrate favorites."""
    print("Migrating favorites...")
    
    for favorite in Favorite.objects.all():
        print(f"Migrating favorite ID: {favorite.id}")
        
        try:
            # Map the user ID and media ID
            supabase_user_id = user_id_map.get(favorite.user_id)
            supabase_media_id = media_id_map.get(favorite.media_id)
            
            if not supabase_user_id:
                print(f"  Warning: Could not find Supabase user ID for Django user ID: {favorite.user_id}")
                continue
                
            if not supabase_media_id:
                print(f"  Warning: Could not find Supabase media ID for Django media ID: {favorite.media_id}")
                continue
            
            # Create favorite in Supabase
            favorite_data = {
                'id': str(uuid.uuid4()),
                'user_id': supabase_user_id,
                'media_id': supabase_media_id,
                'created_at': favorite.created_at.isoformat() if favorite.created_at else datetime.now().isoformat()
            }
            
            supabase.table('favorites').insert(favorite_data).execute()
            print(f"  Favorite migrated for user ID: {supabase_user_id}, media ID: {supabase_media_id}")
            
        except Exception as e:
            print(f"  Error migrating favorite {favorite.id}: {str(e)}")

if __name__ == "__main__":
    main() 