from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from .models import UserProfile, Album, Media, Favorite
from .forms import UserProfileForm, AlbumForm, MediaForm, CombinedProfileForm
from django.db.models import Q
from django.core.exceptions import ValidationError
from .supabase_auth import SupabaseAuthBackend
from functools import wraps
from savesphere.supabase import get_supabase_client

def login_required(view_func):
    """Custom login_required decorator to check for user_id in session"""
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        user_id = request.session.get('user_id')
        if not user_id:
            messages.error(request, "Please log in to access this page.")
            return redirect('savesphere_app:login')
        return view_func(request, *args, **kwargs)
    return wrapped_view

def is_admin(user):
    return user.get('role') == 'admin'

def is_staff(user):
    return user.get('role') in ['admin', 'staff']

@login_required
def dashboard(request):
    user_id = request.session.get('user_id')
    user_media = Media.objects.filter(user_id=user_id).order_by('-created_at')
    user_albums = Album.objects.filter(user_id=user_id)
    
    # Calculate storage usage
    total_storage = 0
    for media in user_media:
        if media.file:
            total_storage += media.file.size
    
    # Convert to appropriate unit
    storage_used = format_file_size(total_storage)
    storage_available = "5.0 GB"  # Assuming 5GB limit
    storage_percentage = min((total_storage / (5 * 1024 * 1024 * 1024)) * 100, 100)  # 5GB in bytes
    
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
    edit_mode = request.GET.get('edit', False)
    user_id = request.session.get('user_id')
    user_profile = get_object_or_404(UserProfile, user_id=user_id)
    
    if request.method == 'POST':
        form = CombinedProfileForm(request.POST, request.FILES, instance=user_profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('savesphere_app:profile')
    else:
        form = CombinedProfileForm(instance=user_profile)
    
    return render(request, 'savesphere_app/profile.html', {
        'form': form,
        'edit_mode': edit_mode
    })

@login_required
def album_list(request):
    user_id = request.session.get('user_id')
    albums = Album.objects.filter(user_id=user_id)
    return render(request, 'savesphere_app/album_list.html', {'albums': albums})

@login_required
def album_create(request):
    user_id = request.session.get('user_id')
    if request.method == 'POST':
        form = AlbumForm(request.POST)
        if form.is_valid():
            album = form.save(commit=False)
            album.user_id = user_id
            album.save()
            messages.success(request, 'Album created successfully!')
            return redirect('savesphere_app:album_list')
    else:
        form = AlbumForm()
    return render(request, 'savesphere_app/album_form.html', {'form': form})

@login_required
def media_upload(request):
    user_id = request.session.get('user_id')
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        album_id = request.POST.get('album')
        file = request.FILES.get('file')
        add_to_favorites = request.POST.get('favorite') == 'on'

        if file:
            # Automatically detect media type from file
            content_type = file.content_type
            if content_type.startswith('image/'):
                media_type = 'photo'
            elif content_type.startswith('video/'):
                media_type = 'video'
            else:
                messages.error(request, 'Invalid file type. Please upload an image or video file.')
                return redirect('savesphere_app:media_upload')

            # Get user's storage info
            user_profile = get_object_or_404(UserProfile, user_id=user_id)
            file_size_mb = file.size / (1024 * 1024)  # Convert bytes to MB

            # Check if upload would exceed quota
            storage_quota_mb = user_profile.storage_quota / (1024 * 1024)  # Convert bytes to MB
            storage_used_mb = user_profile.storage_used / (1024 * 1024)  # Convert bytes to MB

            if storage_used_mb + file_size_mb > storage_quota_mb:
                messages.error(request, 'Upload would exceed your storage quota.')
                return redirect('savesphere_app:media_upload')

            try:
                # Create the media object
                media = Media.objects.create(
                    user_id=user_id,
                    title=title,
                    description=description,
                    file=file,
                    media_type=media_type
                )

                # Add to album if specified
                if album_id:
                    album = Album.objects.get(id=album_id, user_id=user_id)
                    album.media.add(media)

                # Add to favorites if checked
                if add_to_favorites:
                    Favorite.objects.create(user_id=user_id, media=media)

                # Update user's storage usage (keep it in bytes in the database)
                user_profile.storage_used += file.size  # Store in bytes
                user_profile.save()

                messages.success(request, 'Media uploaded successfully!')
                return redirect('savesphere_app:dashboard')

            except Exception as e:
                messages.error(request, f'Error uploading media: {str(e)}')
                return redirect('savesphere_app:media_upload')

    # Get user's storage information
    user_profile = get_object_or_404(UserProfile, user_id=user_id)
    storage_used_mb = user_profile.storage_used / (1024 * 1024)  # Convert bytes to MB
    storage_quota_mb = user_profile.storage_quota / (1024 * 1024)  # Convert bytes to MB
    storage_percentage = round((storage_used_mb / storage_quota_mb) * 100, 1) if storage_quota_mb > 0 else 0

    # Get user's albums for the dropdown
    albums = Album.objects.filter(user_id=user_id)

    context = {
        'albums': albums,
        'storage_used': round(storage_used_mb, 2),  # Round to 2 decimal places
        'storage_quota': round(storage_quota_mb, 2),  # Round to 2 decimal places
        'storage_percentage': storage_percentage,
        'max_file_size': 100  # Maximum file size in MB
    }

    return render(request, 'savesphere_app/media_upload.html', context)

@login_required
def media_detail(request, pk):
    user_id = request.session.get('user_id')
    media = get_object_or_404(Media, pk=pk, user_id=user_id)
    return render(request, 'savesphere_app/media_detail.html', {'media': media})

@login_required
def admin_dashboard(request):
    # Check if user is admin
    user_id = request.session.get('user_id')
    user_profile = get_object_or_404(UserProfile, user_id=user_id)
    
    if user_profile.role != 'admin':
        messages.error(request, "You don't have permission to access this page.")
        return redirect('savesphere_app:dashboard')
    
    # Get total counts
    total_users = UserProfile.objects.count()
    active_users = UserProfile.objects.filter(is_blocked_upload=False).count()
    total_media = Media.objects.count()
    total_albums = Album.objects.count()
    
    # Calculate storage usage
    total_storage = 0
    for media in Media.objects.all():
        if media.file:
            total_storage += media.file.size
    
    # Convert to appropriate unit
    storage_used = format_file_size(total_storage)
    storage_percentage = min((total_storage / (5 * 1024 * 1024 * 1024)) * 100, 100)  # Assuming 5GB limit
    
    # Get recent activities (last 10)
    recent_activities = []  # This will be replaced with actual activity tracking
    
    context = {
        'total_users': total_users,
        'active_users': active_users,
        'total_media': total_media,
        'total_albums': total_albums,
        'storage_used': storage_used,
        'storage_percentage': storage_percentage,
        'recent_activities': recent_activities,
        'is_admin': True  # Add this to indicate admin context
    }
    return render(request, 'savesphere_app/admin_dashboard.html', context)

def format_file_size(size):
    """Convert file size to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"

@login_required
def user_management(request):
    # Check if user is admin or staff
    user_id = request.session.get('user_id')
    user_profile = get_object_or_404(UserProfile, user_id=user_id)
    
    if user_profile.role not in ['admin', 'staff']:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('savesphere_app:dashboard')
    
    # Get all users except the current user
    users_queryset = UserProfile.objects.exclude(user_id=user_id)
    
    # Apply filters
    search_query = request.GET.get('search', '')
    status = request.GET.get('status', '')
    role = request.GET.get('role', '')
    
    if search_query:
        users_queryset = users_queryset.filter(
            Q(email__icontains=search_query)
        )
    
    if status:
        is_blocked = status == 'blocked'
        users_queryset = users_queryset.filter(is_blocked_upload=is_blocked)
    
    # Pagination
    paginator = Paginator(users_queryset, 9)  # Show 9 users per page
    page = request.GET.get('page')
    users = paginator.get_page(page)
    
    context = {
        'users': users,
        'is_paginated': users.has_other_pages(),
        'page_obj': users,
    }
    
    return render(request, 'savesphere_app/user_management.html', context)

@login_required
def add_user(request):
    # Check if user is admin or staff
    user_id = request.session.get('user_id')
    user_profile = get_object_or_404(UserProfile, user_id=user_id)
    
    if user_profile.role not in ['admin', 'staff']:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('savesphere_app:dashboard')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        is_active = request.POST.get('is_active') == 'on'
        is_staff = request.POST.get('is_staff') == 'on'
        
        try:
            # Create Supabase user
            supabase = get_supabase_client()
            auth_response = supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            
            if auth_response.user:
                # Create user profile
                new_profile = UserProfile.objects.create(
                    user_id=auth_response.user.id,
                    email=email,
                    is_blocked_upload=not is_active,
                    role='staff' if is_staff else 'user'
                )
                messages.success(request, f'User "{email}" has been created successfully.')
            else:
                messages.error(request, "Failed to create user in Supabase.")
        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')
    
    return redirect('savesphere_app:user_management')

@login_required
def edit_user(request, user_id):
    # Check if current user is admin or staff
    current_user_id = request.session.get('user_id')
    current_user_profile = get_object_or_404(UserProfile, user_id=current_user_id)
    
    if current_user_profile.role not in ['admin', 'staff']:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('savesphere_app:dashboard')
    
    try:
        user_profile = UserProfile.objects.get(user_id=user_id)
        if request.method == 'POST':
            email = request.POST.get('email')
            is_active = request.POST.get('is_active') == 'on'
            is_staff = request.POST.get('is_staff') == 'on'
            storage_limit = request.POST.get('storage_limit')
            
            try:
                # Update user profile fields
                user_profile.email = email
                user_profile.is_blocked_upload = not is_active
                user_profile.role = 'staff' if is_staff else 'user'
                
                if storage_limit:
                    # Convert MB to bytes
                    user_profile.storage_quota = int(float(storage_limit) * 1024 * 1024)
                user_profile.save()
                
                messages.success(request, f'User "{email}" has been updated successfully.')
            except Exception as e:
                messages.error(request, f'Error updating user: {str(e)}')
    except UserProfile.DoesNotExist:
        messages.error(request, 'User not found.')
    
    return redirect('savesphere_app:user_management')

@login_required
def delete_user(request, user_id):
    # Check if current user is admin or staff
    current_user_id = request.session.get('user_id')
    current_user_profile = get_object_or_404(UserProfile, user_id=current_user_id)
    
    if current_user_profile.role not in ['admin', 'staff']:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('savesphere_app:dashboard')
    
    if request.method == 'POST':
        # Prevent deleting your own user
        if user_id == current_user_id:
            messages.error(request, "You cannot delete your own user account.")
            return redirect('savesphere_app:user_management')
        
        try:
            user_profile = UserProfile.objects.get(user_id=user_id)
            email = user_profile.email
            
            # Delete from Supabase
            try:
                supabase = get_supabase_client()
                # Note: This assumes admin permissions in Supabase
                # You might need to implement this differently based on Supabase permissions
                # supabase.auth.admin.delete_user(user_id)
            except Exception as e:
                print(f"Error deleting user from Supabase: {str(e)}")
            
            # Delete user profile from Django database
            user_profile.delete()
            messages.success(request, f'User "{email}" has been deleted successfully.')
        except UserProfile.DoesNotExist:
            messages.error(request, 'User not found.')
        except Exception as e:
            messages.error(request, f'Error deleting user: {str(e)}')
    
    return redirect('savesphere_app:user_management')

@login_required
def content_management(request):
    # Check if user is admin or staff
    user_id = request.session.get('user_id')
    user_profile = get_object_or_404(UserProfile, user_id=user_id)
    
    if user_profile.role not in ['admin', 'staff']:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('savesphere_app:dashboard')
    
    content_type = request.GET.get('type', 'all')
    
    if content_type == 'media':
        media_list = Media.objects.all()
        album_list = []
    elif content_type == 'album':
        media_list = []
        album_list = Album.objects.prefetch_related('media').all()
    else:  # 'all'
        media_list = Media.objects.all()
        album_list = Album.objects.prefetch_related('media').all()
    
    contents = []
    
    if content_type != 'album':
        for media in media_list:
            contents.append({
                'id': media.id,
                'type': 'media',
                'title': media.title,
                'user_id': media.user_id,
                'created_at': media.created_at,
                'is_public': media.is_public,
                'file': media.file,
                'media_type': media.media_type,
            })
    
    if content_type != 'media':
        for album in album_list:
            media_count = album.media.count()
            contents.append({
                'id': album.id,
                'type': 'album',
                'title': album.name,
                'user_id': album.user_id,
                'created_at': album.created_at,
                'is_public': album.is_public,
                'media_count': media_count,
            })
    
    # Sort combined content by date (newest first)
    contents.sort(key=lambda x: x['created_at'], reverse=True)
    
    # Pagination
    paginator = Paginator(contents, 9)  # Show 9 items per page
    page = request.GET.get('page')
    contents = paginator.get_page(page)
    
    context = {
        'contents': contents,
        'is_paginated': contents.has_other_pages(),
        'page_obj': contents,
        'current_type': content_type,
    }
    
    return render(request, 'savesphere_app/content_management.html', context)

@login_required
def edit_media(request, media_id):
    # Check if user is admin or staff
    user_id = request.session.get('user_id')
    user_profile = get_object_or_404(UserProfile, user_id=user_id)
    
    if user_profile.role not in ['admin', 'staff']:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('savesphere_app:dashboard')
    
    if request.method == 'POST':
        media = get_object_or_404(Media, id=media_id)
        title = request.POST.get('title')
        is_public = request.POST.get('is_public') == 'on'
        
        try:
            media.title = title
            media.is_public = is_public
            media.save()
            messages.success(request, f'Media "{title}" has been updated successfully.')
        except Exception as e:
            messages.error(request, f'Error updating media: {str(e)}')
    
    return redirect('savesphere_app:content_management')

@login_required
def edit_album(request, album_id):
    # Check if user is admin or staff
    user_id = request.session.get('user_id')
    user_profile = get_object_or_404(UserProfile, user_id=user_id)
    
    if user_profile.role not in ['admin', 'staff']:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('savesphere_app:dashboard')
    
    if request.method == 'POST':
        album = get_object_or_404(Album, id=album_id)
        name = request.POST.get('title')  # Get title from form
        is_public = request.POST.get('is_public') == 'on'
        
        try:
            album.name = name  # Update name instead of title
            album.is_public = is_public
            album.save()
            messages.success(request, f'Album "{name}" has been updated successfully.')
        except Exception as e:
            messages.error(request, f'Error updating album: {str(e)}')
    
    return redirect('savesphere_app:content_management')

@login_required
def delete_media(request, media_id):
    # Check if user is admin or staff
    user_id = request.session.get('user_id')
    user_profile = get_object_or_404(UserProfile, user_id=user_id)
    
    if user_profile.role not in ['admin', 'staff']:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('savesphere_app:dashboard')
    
    if request.method == 'POST':
        media = get_object_or_404(Media, id=media_id)
        title = media.title
        
        try:
            # Update storage used for the owner
            owner_id = media.user_id
            if owner_id:
                try:
                    owner_profile = UserProfile.objects.get(user_id=owner_id)
                    owner_profile.storage_used = max(0, owner_profile.storage_used - media.file.size)
                    owner_profile.save()
                except UserProfile.DoesNotExist:
                    pass
            
            media.delete()
            messages.success(request, f'Media "{title}" has been deleted successfully.')
        except Exception as e:
            messages.error(request, f'Error deleting media: {str(e)}')
    
    return redirect('savesphere_app:content_management')

@login_required
def delete_album(request, album_id):
    # Check if user is admin or staff
    user_id = request.session.get('user_id')
    user_profile = get_object_or_404(UserProfile, user_id=user_id)
    
    if user_profile.role not in ['admin', 'staff']:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('savesphere_app:dashboard')
    
    if request.method == 'POST':
        album = get_object_or_404(Album, id=album_id)
        name = album.name
        
        try:
            album.delete()
            messages.success(request, f'Album "{name}" has been deleted successfully.')
        except Exception as e:
            messages.error(request, f'Error deleting album: {str(e)}')
    
    return redirect('savesphere_app:content_management')

@login_required
def bulk_content_action(request):
    # Check if user is admin or staff
    user_id = request.session.get('user_id')
    user_profile = get_object_or_404(UserProfile, user_id=user_id)
    
    if user_profile.role not in ['admin', 'staff']:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('savesphere_app:dashboard')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        content_type = request.POST.get('content_type')
        
        try:
            if action == 'make_public':
                if content_type in ['all', 'media']:
                    Media.objects.update(is_public=True)
                if content_type in ['all', 'albums']:
                    Album.objects.update(is_public=True)
                messages.success(request, 'Selected content has been made public.')
            
            elif action == 'make_private':
                if content_type in ['all', 'media']:
                    Media.objects.update(is_public=False)
                if content_type in ['all', 'albums']:
                    Album.objects.update(is_public=False)
                messages.success(request, 'Selected content has been made private.')
            
            elif action == 'delete':
                if content_type in ['all', 'media']:
                    Media.objects.all().delete()
                if content_type in ['all', 'albums']:
                    Album.objects.all().delete()
                messages.success(request, 'Selected content has been deleted.')
            
        except Exception as e:
            messages.error(request, f'Error performing bulk action: {str(e)}')
    
    return redirect('savesphere_app:content_management')

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create UserProfile
            UserProfile.objects.create(user=user)
            messages.success(request, 'Account created successfully! You can now login.')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'savesphere_app/register.html', {'form': form})

@login_required
def profile(request):
    return render(request, 'savesphere_app/profile.html')

@login_required
def album_edit(request, pk):
    user_id = request.session.get('user_id')
    album = get_object_or_404(Album, pk=pk, user_id=user_id)
    if request.method == 'POST':
        form = AlbumForm(request.POST, instance=album)
        if form.is_valid():
            form.save()
            messages.success(request, 'Album updated successfully!')
            return redirect('savesphere_app:album_list')
    else:
        form = AlbumForm(instance=album)
    return render(request, 'savesphere_app/album_form.html', {
        'form': form,
        'album': album,
        'is_edit': True
    })

@login_required
def album_delete(request, pk):
    album = get_object_or_404(Album, pk=pk, user=request.user)
    if request.method == 'POST':
        album.delete()
        messages.success(request, 'Album deleted successfully!')
        return redirect('savesphere_app:album_list')
    return redirect('savesphere_app:album_list')

@login_required
def album_detail(request, pk):
    album = get_object_or_404(Album, pk=pk, user=request.user)
    media = Media.objects.filter(album=album)
    return render(request, 'savesphere_app/album_detail.html', {
        'album': album,
        'media': media
    })

@login_required
def media_delete(request, pk):
    media = get_object_or_404(Media, pk=pk, user=request.user)
    file_size = media.file.size
    album = media.album  # Store the album before deleting the media
    
    if request.method == 'POST':
        # Update storage used
        user_profile = request.user.userprofile
        user_profile.storage_used = max(0, user_profile.storage_used - file_size)
        user_profile.save()
        
        media.delete()
        messages.success(request, 'Media deleted successfully!')
        if album:
            return redirect('savesphere_app:album_detail', pk=album.pk)
        return redirect('savesphere_app:dashboard')
    return redirect('savesphere_app:media_detail', pk=pk)

def home(request):
    """Landing page view for non-logged in users"""
    if request.user.is_authenticated:
        return redirect('savesphere_app:dashboard')
    return render(request, 'savesphere_app/home.html')

@login_required
def favorite_list(request):
    """View to display user's favorite media"""
    user_id = request.session.get('user_id')
    favorites = Favorite.objects.filter(user_id=user_id).select_related('media')
    return render(request, 'savesphere_app/favorite_list.html', {'favorites': favorites})

@login_required
def toggle_favorite(request, media_id):
    """Toggle favorite status for a media item"""
    user_id = request.session.get('user_id')
    
    if request.method == 'POST':
        media = get_object_or_404(Media, id=media_id)
        favorite, created = Favorite.objects.get_or_create(user_id=user_id, media=media)
        if not created:
            favorite.delete()
        return JsonResponse({
            'status': 'success',
            'is_favorite': created
        })
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def storage_management(request):
    # Check if user is admin
    user_id = request.session.get('user_id')
    user_profile = get_object_or_404(UserProfile, user_id=user_id)
    
    if user_profile.role != 'admin':
        messages.error(request, "You don't have permission to access this page.")
        return redirect('savesphere_app:dashboard')
    
    users = UserProfile.objects.all()
    
    if request.method == 'POST':
        target_user_id = request.POST.get('user_id')
        new_quota = request.POST.get('new_quota')
        
        try:
            user_profile = UserProfile.objects.get(user_id=target_user_id)
            new_quota_bytes = int(float(new_quota) * 1024 * 1024)  # Convert MB to bytes
            user_profile.storage_quota = new_quota_bytes
            user_profile.save()
            messages.success(request, f'Storage quota updated for {user_profile.email}')
        except (UserProfile.DoesNotExist, ValueError) as e:
            messages.error(request, f'Error updating quota: {str(e)}')
        
        return redirect('savesphere_app:storage_management')
    
    return render(request, 'savesphere_app/storage_management.html', {'users': users})

@login_required
def media_list(request):
    """View for listing all media items."""
    user_media = Media.objects.filter(user=request.user).order_by('-uploaded_at')
    return render(request, 'savesphere_app/media_list.html', {
        'media': user_media,
    })

@login_required
def search(request):
    user_id = request.session.get('user_id')
    query = request.GET.get('q', '')
    if query:
        # Search in media
        media_results = Media.objects.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query),
            user_id=user_id
        )
        
        # Search in albums
        album_results = Album.objects.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query),
            user_id=user_id
        )
    else:
        media_results = Media.objects.none()
        album_results = Album.objects.none()
    
    context = {
        'query': query,
        'media_results': media_results,
        'album_results': album_results,
        'has_results': media_results.exists() or album_results.exists()
    }
    return render(request, 'savesphere_app/search_results.html', context) 