"""
Supabase database operations for SaveSphere app.
"""

import uuid
import json
from datetime import datetime
from savesphere.supabase import get_supabase_client
from django.conf import settings

# Get the supabase client when needed
def get_client():
    return get_supabase_client()

class SupabaseUser:
    """User operations with Supabase."""
    
    @staticmethod
    def create_user(email, password, username):
        """Create a new user in Supabase Auth."""
        try:
            # Create user in Supabase Auth
            user_data = get_client().auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "username": username
                    }
                }
            })
            
            # Create user profile in the 'profiles' table
            get_client().table('profiles').insert({
                'id': user_data.user.id,
                'username': username,
                'bio': '',
                'storage_quota': 104857600,  # 100MB in bytes
                'storage_used': 0,
                'is_blocked_upload': False,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }).execute()
            
            return user_data.user
        except Exception as e:
            raise Exception(f"Error creating user: {str(e)}")
    
    @staticmethod
    def get_user_profile(user_id):
        """Get a user profile from Supabase."""
        try:
            result = get_client().table('profiles').select('*').eq('id', user_id).execute()
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
        except Exception as e:
            raise Exception(f"Error getting user profile: {str(e)}")
    
    @staticmethod
    def update_user_profile(user_id, profile_data):
        """Update a user profile in Supabase."""
        try:
            profile_data['updated_at'] = datetime.now().isoformat()
            result = get_client().table('profiles').update(profile_data).eq('id', user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            raise Exception(f"Error updating user profile: {str(e)}")
    
    @staticmethod
    def get_all_users():
        """Get all users from Supabase."""
        try:
            result = get_client().table('profiles').select('*').execute()
            return result.data
        except Exception as e:
            raise Exception(f"Error getting all users: {str(e)}")
    
    @staticmethod
    def delete_user(user_id):
        """Delete a user and all their data."""
        try:
            # Delete user's media
            SupabaseMedia.delete_user_media(user_id)
            
            # Delete user's albums
            SupabaseAlbum.delete_user_albums(user_id)
            
            # Delete user profile
            get_client().table('profiles').delete().eq('id', user_id).execute()
            
            # Delete user from auth
            get_client().auth.admin.delete_user(user_id)
            
            return True
        except Exception as e:
            raise Exception(f"Error deleting user: {str(e)}")


class SupabaseAlbum:
    """Album operations with Supabase."""
    
    @staticmethod
    def create_album(user_id, name, description, is_public=False):
        """Create a new album in Supabase."""
        try:
            album_id = str(uuid.uuid4())
            data = {
                'id': album_id,
                'user_id': user_id,
                'name': name,
                'description': description,
                'is_public': is_public,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            result = get_client().table('albums').insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            raise Exception(f"Error creating album: {str(e)}")
    
    @staticmethod
    def get_album(album_id):
        """Get album details from Supabase."""
        try:
            result = get_client().table('albums').select('*').eq('id', album_id).execute()
            return result.data[0] if result.data and len(result.data) > 0 else None
        except Exception as e:
            raise Exception(f"Error getting album: {str(e)}")
    
    @staticmethod
    def get_user_albums(user_id):
        """Get all albums for a user from Supabase."""
        try:
            result = get_client().table('albums').select('*').eq('user_id', user_id).order('created_at', desc=True).execute()
            return result.data
        except Exception as e:
            raise Exception(f"Error getting user albums: {str(e)}")
    
    @staticmethod
    def update_album(album_id, user_id, album_data):
        """Update an album in Supabase."""
        try:
            album_data['updated_at'] = datetime.now().isoformat()
            result = get_client().table('albums').update(album_data).eq('id', album_id).eq('user_id', user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            raise Exception(f"Error updating album: {str(e)}")
    
    @staticmethod
    def delete_album(album_id, user_id):
        """Delete an album from Supabase."""
        try:
            # First, remove all media from this album
            media_result = get_client().table('media').select('id').eq('album_id', album_id).execute()
            for media in media_result.data:
                get_client().table('media').update({'album_id': None}).eq('id', media['id']).execute()
            
            # Then delete the album
            result = get_client().table('albums').delete().eq('id', album_id).eq('user_id', user_id).execute()
            return True
        except Exception as e:
            raise Exception(f"Error deleting album: {str(e)}")
    
    @staticmethod
    def delete_user_albums(user_id):
        """Delete all albums for a user."""
        try:
            # First, remove album_id from all media
            media_result = get_client().table('media').select('id').eq('user_id', user_id).execute()
            for media in media_result.data:
                get_client().table('media').update({'album_id': None}).eq('id', media['id']).execute()
            
            # Then delete all albums
            get_client().table('albums').delete().eq('user_id', user_id).execute()
            return True
        except Exception as e:
            raise Exception(f"Error deleting user albums: {str(e)}")


class SupabaseMedia:
    """Media operations with Supabase."""
    
    @staticmethod
    def create_media(user_id, title, description, file_path, media_type, album_id=None, is_public=False):
        """Upload media file to Supabase Storage and create record."""
        try:
            media_id = str(uuid.uuid4())
            
            # Upload file to Supabase Storage
            with open(file_path, 'rb') as f:
                file_content = f.read()
                file_size = len(file_content)
                
                # Generate a unique path in the bucket
                storage_path = f"{user_id}/{media_id}/{file_path.split('/')[-1]}"
                
                # Upload the file
                get_client().storage.from_(settings.SUPABASE_BUCKET).upload(
                    storage_path,
                    file_content
                )
                
                # Get public URL
                file_url = get_client().storage.from_(settings.SUPABASE_BUCKET).get_public_url(storage_path)
                
                # Create media record in database
                media_data = {
                    'id': media_id,
                    'user_id': user_id,
                    'album_id': album_id,
                    'title': title,
                    'description': description,
                    'media_type': media_type,
                    'file_url': file_url,
                    'file_size': file_size,
                    'storage_path': storage_path,
                    'is_public': is_public,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                
                result = get_client().table('media').insert(media_data).execute()
                
                # Update user's storage usage
                user_profile = SupabaseUser.get_user_profile(user_id)
                if user_profile:
                    SupabaseUser.update_user_profile(
                        user_id, 
                        {'storage_used': user_profile['storage_used'] + file_size}
                    )
                
                return result.data[0] if result.data else None
        except Exception as e:
            raise Exception(f"Error creating media: {str(e)}")
    
    @staticmethod
    def get_media(media_id):
        """Get media details from Supabase."""
        try:
            result = get_client().table('media').select('*').eq('id', media_id).execute()
            return result.data[0] if result.data and len(result.data) > 0 else None
        except Exception as e:
            raise Exception(f"Error getting media: {str(e)}")
    
    @staticmethod
    def get_user_media(user_id):
        """Get all media for a user from Supabase."""
        try:
            result = get_client().table('media').select('*').eq('user_id', user_id).order('created_at', desc=True).execute()
            return result.data
        except Exception as e:
            raise Exception(f"Error getting user media: {str(e)}")
    
    @staticmethod
    def get_album_media(album_id):
        """Get all media in an album from Supabase."""
        try:
            result = get_client().table('media').select('*').eq('album_id', album_id).order('created_at', desc=True).execute()
            return result.data
        except Exception as e:
            raise Exception(f"Error getting album media: {str(e)}")
    
    @staticmethod
    def update_media(media_id, user_id, media_data):
        """Update media details in Supabase."""
        try:
            media_data['updated_at'] = datetime.now().isoformat()
            result = get_client().table('media').update(media_data).eq('id', media_id).eq('user_id', user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            raise Exception(f"Error updating media: {str(e)}")
    
    @staticmethod
    def delete_media(media_id, user_id):
        """Delete media from Supabase Storage and database."""
        try:
            # Get media data first to get the storage path and file size
            media = SupabaseMedia.get_media(media_id)
            if not media or media['user_id'] != user_id:
                raise Exception("Media not found or not owned by user")
            
            # Delete file from storage
            get_client().storage.from_(settings.SUPABASE_BUCKET).remove([media['storage_path']])
            
            # Delete from favorites
            get_client().table('favorites').delete().eq('media_id', media_id).execute()
            
            # Delete media record
            get_client().table('media').delete().eq('id', media_id).eq('user_id', user_id).execute()
            
            # Update user's storage usage
            user_profile = SupabaseUser.get_user_profile(user_id)
            if user_profile:
                new_storage_used = max(0, user_profile['storage_used'] - media['file_size'])
                SupabaseUser.update_user_profile(user_id, {'storage_used': new_storage_used})
            
            return True
        except Exception as e:
            raise Exception(f"Error deleting media: {str(e)}")
    
    @staticmethod
    def delete_user_media(user_id):
        """Delete all media for a user."""
        try:
            # Get all media for user
            media_result = get_client().table('media').select('*').eq('user_id', user_id).execute()
            
            # Delete each file from storage
            for media in media_result.data:
                get_client().storage.from_(settings.SUPABASE_BUCKET).remove([media['storage_path']])
            
            # Delete from favorites
            media_ids = [media['id'] for media in media_result.data]
            if media_ids:
                get_client().table('favorites').delete().in_('media_id', media_ids).execute()
            
            # Delete all media records
            get_client().table('media').delete().eq('user_id', user_id).execute()
            
            # Reset user's storage usage
            SupabaseUser.update_user_profile(user_id, {'storage_used': 0})
            
            return True
        except Exception as e:
            raise Exception(f"Error deleting user media: {str(e)}")


class SupabaseFavorite:
    """Favorite operations with Supabase."""
    
    @staticmethod
    def add_favorite(user_id, media_id):
        """Add a media item to user's favorites."""
        try:
            # Check if already favorited
            result = get_client().table('favorites').select('*').eq('user_id', user_id).eq('media_id', media_id).execute()
            if result.data and len(result.data) > 0:
                return result.data[0]
            
            # Add to favorites
            favorite_data = {
                'id': str(uuid.uuid4()),
                'user_id': user_id,
                'media_id': media_id,
                'created_at': datetime.now().isoformat()
            }
            result = get_client().table('favorites').insert(favorite_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            raise Exception(f"Error adding favorite: {str(e)}")
    
    @staticmethod
    def remove_favorite(user_id, media_id):
        """Remove a media item from user's favorites."""
        try:
            result = get_client().table('favorites').delete().eq('user_id', user_id).eq('media_id', media_id).execute()
            return True
        except Exception as e:
            raise Exception(f"Error removing favorite: {str(e)}")
    
    @staticmethod
    def get_user_favorites(user_id):
        """Get all favorites for a user from Supabase."""
        try:
            # Get user's favorites with media data
            result = get_client().table('favorites')\
                .select('favorites.id, favorites.created_at, media:media(*)')\
                .eq('user_id', user_id)\
                .order('created_at', desc=True)\
                .execute()
                
            # Process the nested data to simplify structure
            processed_data = []
            for item in result.data:
                media_data = item.get('media', {})
                processed_item = {
                    'id': item['id'],
                    'created_at': item['created_at'],
                    'media': media_data
                }
                processed_data.append(processed_item)
                
            return processed_data
        except Exception as e:
            raise Exception(f"Error getting user favorites: {str(e)}")
    
    @staticmethod
    def is_favorite(user_id, media_id):
        """Check if a media item is in user's favorites."""
        try:
            result = get_client().table('favorites').select('*').eq('user_id', user_id).eq('media_id', media_id).execute()
            return len(result.data) > 0
        except Exception as e:
            raise Exception(f"Error checking favorite: {str(e)}") 