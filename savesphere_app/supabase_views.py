"""
Views for SaveSphere app using Supabase operations.
"""

import os
import uuid
import tempfile
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.contrib.auth import logout
from django.conf import settings

from .supabase_operations import (
    SupabaseUser, 
    SupabaseAlbum, 
    SupabaseMedia, 
    SupabaseFavorite
)
from .forms import AlbumForm, MediaForm, UserProfileForm, CombinedProfileForm
from savesphere.supabase import get_supabase_client

supabase = get_supabase_client()

def is_admin(user):
    """Check if user is admin."""
    return user.is_staff

def is_staff(user):
    """Check if user is staff."""
    return user.is_staff

def format_file_size(size_bytes):
    """Format bytes to human-readable size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes/(1024*1024):.1f} MB"
    else:
        return f"{size_bytes/(1024*1024*1024):.1f} GB"

def extract_user_id(request):
    """Extract user_id from request."""
    # Get the JWT token from session or cookie
    access_token = request.session.get('supabase_access_token')
    if not access_token:
        # If not in session, try to get from cookies
        access_token = request.COOKIES.get('supabase_access_token')
    
    if not access_token:
        return None
    
    # Get user information from the token
    try:
        user = supabase.auth.get_user(access_token)
        return user.user.id
    except Exception:
        # Token may be expired or invalid
        return None

@login_required
def search(request):
    """Search for media and albums."""
    user_id = extract_user_id(request)
    if not user_id:
        logout(request)
        return redirect('login')
    
    query = request.GET.get('q', '')
    search_type = request.GET.get('type', 'all')
    
    results = {
        'media': [],
        'albums': []
    }
    
    if not query:
        return render(request, 'savesphere_app/search_results.html', {
            'query': query,
            'results': results,
            'search_type': search_type
        })
    
    try:
        # Search for media
        if search_type in ['all', 'media']:
            media_results = supabase.table('media').select('*').eq('user_id', user_id).ilike('title', f'%{query}%').execute()
            results['media'] = media_results.data
        
        # Search for albums
        if search_type in ['all', 'albums']:
            album_results = supabase.table('albums').select('*').eq('user_id', user_id).ilike('name', f'%{query}%').execute()
            results['albums'] = album_results.data
    except Exception as e:
        messages.error(request, f"Search error: {str(e)}")
    
    return render(request, 'savesphere_app/search_results.html', {
        'query': query,
        'results': results,
        'search_type': search_type
    })

@login_required
def dashboard(request):
    """Dashboard view with user's media and albums."""
    user_id = extract_user_id(request)
    if not user_id:
        # If user_id can't be extracted, logout and redirect to login
        logout(request)
        return redirect('login')
        
    # Get user's media and albums
    user_media = SupabaseMedia.get_user_media(user_id)
    user_albums = SupabaseAlbum.get_user_albums(user_id)
    
    # Get user profile for storage information
    user_profile = SupabaseUser.get_user_profile(user_id)
    
    # Calculate storage info
    storage_used_bytes = user_profile.get('storage_used', 0)
    storage_quota_bytes = user_profile.get('storage_quota', 104857600)  # Default to 100MB
    
    storage_used = format_file_size(storage_used_bytes)
    storage_available = format_file_size(storage_quota_bytes)
    storage_percentage = min((storage_used_bytes / storage_quota_bytes) * 100, 100)
    
    context = {
        'media': user_media,
        'albums': user_albums,
        'storage_used': storage_used,
        'storage_available': storage_available,
        'storage_percentage': storage_percentage,
    }
    
    return render(request, 'savesphere_app/dashboard.html', context)

@login_required
def profile_view(request):
    """User profile view."""
    user_id = extract_user_id(request)
    if not user_id:
        logout(request)
        return redirect('login')
        
    edit_mode = request.GET.get('edit', False)
    user_profile = SupabaseUser.get_user_profile(user_id)
    
    if request.method == 'POST':
        # Process form submission
        form_data = request.POST.copy()
        profile_data = {
            'bio': form_data.get('bio', ''),
        }
        
        # Handle profile picture upload
        if request.FILES.get('profile_picture'):
            profile_pic = request.FILES['profile_picture']
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                for chunk in profile_pic.chunks():
                    temp_file.write(chunk)
                temp_file_path = temp_file.name
            
            # Upload to Supabase Storage
            try:
                storage_path = f"{user_id}/profile/{profile_pic.name}"
                with open(temp_file_path, 'rb') as f:
                    supabase.storage.from_(settings.SUPABASE_BUCKET).upload(
                        storage_path,
                        f.read()
                    )
                
                # Get public URL for the profile picture
                profile_picture_url = supabase.storage.from_(settings.SUPABASE_BUCKET).get_public_url(storage_path)
                profile_data['profile_picture_url'] = profile_picture_url
                
                # Clean up
                os.unlink(temp_file_path)
            except Exception as e:
                messages.error(request, f"Error uploading profile picture: {str(e)}")
        
        # Update the profile
        try:
            SupabaseUser.update_user_profile(user_id, profile_data)
            messages.success(request, 'Profile updated successfully!')
            return redirect('savesphere_app:profile')
        except Exception as e:
            messages.error(request, f"Error updating profile: {str(e)}")
    
    return render(request, 'savesphere_app/profile.html', {
        'profile': user_profile,
        'edit_mode': edit_mode
    })

@login_required
def album_list(request):
    """List all albums for the user."""
    user_id = extract_user_id(request)
    if not user_id:
        logout(request)
        return redirect('login')
        
    albums = SupabaseAlbum.get_user_albums(user_id)
    return render(request, 'savesphere_app/album_list.html', {'albums': albums})

@login_required
def album_create(request):
    """Create a new album."""
    user_id = extract_user_id(request)
    if not user_id:
        logout(request)
        return redirect('login')
        
    if request.method == 'POST':
        form = AlbumForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            description = form.cleaned_data['description']
            is_public = form.cleaned_data.get('is_public', False)
            
            try:
                SupabaseAlbum.create_album(user_id, name, description, is_public)
                messages.success(request, 'Album created successfully!')
                return redirect('savesphere_app:album_list')
            except Exception as e:
                messages.error(request, f"Error creating album: {str(e)}")
    else:
        form = AlbumForm()
        
    return render(request, 'savesphere_app/album_form.html', {'form': form})

@login_required
def album_edit(request, pk):
    """Edit an existing album."""
    user_id = extract_user_id(request)
    if not user_id:
        logout(request)
        return redirect('login')
        
    album = SupabaseAlbum.get_album(pk)
    if not album or album['user_id'] != user_id:
        messages.error(request, "Album not found or you don't have permission to edit it.")
        return redirect('savesphere_app:album_list')
    
    if request.method == 'POST':
        form = AlbumForm(request.POST)
        if form.is_valid():
            album_data = {
                'name': form.cleaned_data['name'],
                'description': form.cleaned_data['description'],
                'is_public': form.cleaned_data.get('is_public', False)
            }
            
            try:
                SupabaseAlbum.update_album(pk, user_id, album_data)
                messages.success(request, 'Album updated successfully!')
                return redirect('savesphere_app:album_list')
            except Exception as e:
                messages.error(request, f"Error updating album: {str(e)}")
    else:
        form = AlbumForm(initial={
            'name': album['name'],
            'description': album['description'],
            'is_public': album['is_public']
        })
        
    return render(request, 'savesphere_app/album_form.html', {'form': form, 'album': album})

@login_required
def album_delete(request, pk):
    """Delete an album."""
    user_id = extract_user_id(request)
    if not user_id:
        logout(request)
        return redirect('login')
        
    album = SupabaseAlbum.get_album(pk)
    if not album or album['user_id'] != user_id:
        messages.error(request, "Album not found or you don't have permission to delete it.")
        return redirect('savesphere_app:album_list')
    
    if request.method == 'POST':
        try:
            SupabaseAlbum.delete_album(pk, user_id)
            messages.success(request, 'Album deleted successfully!')
        except Exception as e:
            messages.error(request, f"Error deleting album: {str(e)}")
        
        return redirect('savesphere_app:album_list')
    
    return render(request, 'savesphere_app/album_confirm_delete.html', {'album': album})

@login_required
def album_detail(request, pk):
    """View album details with its media items."""
    user_id = extract_user_id(request)
    if not user_id:
        logout(request)
        return redirect('login')
        
    album = SupabaseAlbum.get_album(pk)
    if not album or (album['user_id'] != user_id and not album['is_public']):
        messages.error(request, "Album not found or you don't have permission to view it.")
        return redirect('savesphere_app:album_list')
    
    media_items = SupabaseMedia.get_album_media(pk)
    return render(request, 'savesphere_app/album_detail.html', {'album': album, 'media': media_items})

@login_required
def media_upload(request):
    """Upload new media files."""
    user_id = extract_user_id(request)
    if not user_id:
        logout(request)
        return redirect('login')
    
    user_profile = SupabaseUser.get_user_profile(user_id)
    storage_used_bytes = user_profile.get('storage_used', 0)
    storage_quota_bytes = user_profile.get('storage_quota', 104857600)  # Default to 100MB
    storage_used_mb = storage_used_bytes / (1024 * 1024)
    storage_quota_mb = storage_quota_bytes / (1024 * 1024)
    storage_percentage = round((storage_used_mb / storage_quota_mb) * 100, 1) if storage_quota_mb > 0 else 0
    
    # Check if user is blocked from uploading
    if user_profile.get('is_blocked_upload', False):
        messages.error(request, "Your upload privileges have been temporarily suspended.")
        return redirect('savesphere_app:dashboard')
        
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        album_id = request.POST.get('album') if request.POST.get('album') else None
        file = request.FILES.get('file')
        add_to_favorites = request.POST.get('favorite') == 'on'
        is_public = request.POST.get('is_public') == 'on'
        
        if file:
            # Check file size
            file_size_mb = file.size / (1024 * 1024)
            if storage_used_mb + file_size_mb > storage_quota_mb:
                messages.error(request, 'Upload would exceed your storage quota.')
                return redirect('savesphere_app:media_upload')
                
            # Automatically detect media type from file
            content_type = file.content_type
            if content_type.startswith('image/'):
                media_type = 'photo'
            elif content_type.startswith('video/'):
                media_type = 'video'
            else:
                messages.error(request, 'Invalid file type. Please upload an image or video file.')
                return redirect('savesphere_app:media_upload')
                
            try:
                # Create temporary file
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    for chunk in file.chunks():
                        temp_file.write(chunk)
                    temp_file_path = temp_file.name
                
                # Create media in Supabase
                media = SupabaseMedia.create_media(
                    user_id=user_id,
                    title=title,
                    description=description,
                    file_path=temp_file_path,
                    media_type=media_type,
                    album_id=album_id,
                    is_public=is_public
                )
                
                # Clean up temp file
                os.unlink(temp_file_path)
                
                # Add to favorites if requested
                if add_to_favorites and media:
                    SupabaseFavorite.add_favorite(user_id, media['id'])
                
                messages.success(request, 'Media uploaded successfully!')
                return redirect('savesphere_app:dashboard')
                
            except Exception as e:
                messages.error(request, f'Error uploading media: {str(e)}')
                return redirect('savesphere_app:media_upload')
    
    # Get user's albums for the dropdown
    albums = SupabaseAlbum.get_user_albums(user_id)
    
    context = {
        'albums': albums,
        'storage_used': round(storage_used_mb, 2),
        'storage_quota': round(storage_quota_mb, 2),
        'storage_percentage': storage_percentage,
        'max_file_size': 100  # Maximum file size in MB
    }
    
    return render(request, 'savesphere_app/media_upload.html', context)

@login_required
def media_detail(request, pk):
    """View media details."""
    user_id = extract_user_id(request)
    if not user_id:
        logout(request)
        return redirect('login')
        
    media = SupabaseMedia.get_media(pk)
    if not media or (media['user_id'] != user_id and not media['is_public']):
        messages.error(request, "Media not found or you don't have permission to view it.")
        return redirect('savesphere_app:dashboard')
    
    # Check if it's in favorites
    is_favorite = SupabaseFavorite.is_favorite(user_id, pk)
    
    return render(request, 'savesphere_app/media_detail.html', {
        'media': media,
        'is_favorite': is_favorite
    })

@login_required
def media_delete(request, pk):
    """Delete media."""
    user_id = extract_user_id(request)
    if not user_id:
        logout(request)
        return redirect('login')
        
    media = SupabaseMedia.get_media(pk)
    if not media or media['user_id'] != user_id:
        messages.error(request, "Media not found or you don't have permission to delete it.")
        return redirect('savesphere_app:dashboard')
    
    if request.method == 'POST':
        try:
            SupabaseMedia.delete_media(pk, user_id)
            messages.success(request, 'Media deleted successfully!')
        except Exception as e:
            messages.error(request, f"Error deleting media: {str(e)}")
        
        return redirect('savesphere_app:dashboard')
    
    return render(request, 'savesphere_app/media_confirm_delete.html', {'media': media})

@login_required
def toggle_favorite(request, media_id):
    """Toggle favorite status for media."""
    user_id = extract_user_id(request)
    if not user_id:
        return JsonResponse({'success': False, 'error': 'Authentication required'})
    
    try:
        media = SupabaseMedia.get_media(media_id)
        if not media:
            return JsonResponse({'success': False, 'error': 'Media not found'})
        
        is_favorite = SupabaseFavorite.is_favorite(user_id, media_id)
        
        if is_favorite:
            SupabaseFavorite.remove_favorite(user_id, media_id)
            return JsonResponse({'success': True, 'favorited': False})
        else:
            SupabaseFavorite.add_favorite(user_id, media_id)
            return JsonResponse({'success': True, 'favorited': True})
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def favorite_list(request):
    """List all favorite media for the user."""
    user_id = extract_user_id(request)
    if not user_id:
        logout(request)
        return redirect('login')
    
    favorites = SupabaseFavorite.get_user_favorites(user_id)
    return render(request, 'savesphere_app/favorite_list.html', {'favorites': favorites})

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Admin dashboard with system overview."""
    # Get all users
    users = SupabaseUser.get_all_users()
    
    # Get counts
    total_users = len(users)
    active_users = total_users  # In Supabase, we'd need to customize this logic
    
    # Calculate total storage usage across all users
    total_storage = sum(user.get('storage_used', 0) for user in users)
    storage_used = format_file_size(total_storage)
    
    # Assuming 5GB total storage
    storage_percentage = min((total_storage / (5 * 1024 * 1024 * 1024)) * 100, 100)
    
    context = {
        'total_users': total_users,
        'active_users': active_users,
        'storage_used': storage_used,
        'storage_percentage': storage_percentage,
    }
    
    return render(request, 'savesphere_app/admin_dashboard.html', context)

@login_required
@user_passes_test(is_staff)
def user_management(request):
    """Manage all users."""
    users = SupabaseUser.get_all_users()
    
    return render(request, 'savesphere_app/user_management.html', {'users': users})

@login_required
@user_passes_test(is_staff)
def content_management(request):
    """Manage all content."""
    # Get all media for admin viewing
    content_type = request.GET.get('type', 'all')
    
    # This would need to be modified for Supabase to get all media from all users
    # For simplicity, let's assume there's a special admin endpoint or query
    # that allows getting all media
    # This is a placeholder for actual implementation
    all_media = []  # Placeholder
    
    return render(request, 'savesphere_app/content_management.html', {
        'media': all_media,
        'content_type': content_type
    })

def home(request):
    """Home page."""
    return render(request, 'savesphere_app/home.html') 