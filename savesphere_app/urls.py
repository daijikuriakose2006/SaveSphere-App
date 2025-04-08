from django.urls import path
from . import views
from . import supabase_auth

app_name = 'savesphere_app'

urlpatterns = [
    # Auth URLs
    path('', views.dashboard, name='dashboard'),
    path('login/', supabase_auth.login_view, name='login'),
    path('register/', supabase_auth.register_view, name='register'),
    path('logout/', supabase_auth.logout_view, name='logout'),
    path('password-reset/', supabase_auth.password_reset_request, name='password_reset'),
    path('password-reset/confirm/<str:token>/', supabase_auth.password_reset_confirm, name='password_reset_confirm'),
    
    # Profile and Search
    path('profile/', views.profile_view, name='profile'),
    path('search/', views.search, name='search'),
    
    # Album URLs
    path('albums/', views.album_list, name='album_list'),
    path('albums/create/', views.album_create, name='album_create'),
    path('albums/<str:pk>/', views.album_detail, name='album_detail'),
    path('albums/<str:pk>/edit/', views.album_edit, name='album_edit'),
    path('albums/<str:pk>/delete/', views.album_delete, name='album_delete'),
    
    # Media URLs
    path('media/upload/', views.media_upload, name='media_upload'),
    path('media/<str:pk>/', views.media_detail, name='media_detail'),
    path('media/<str:pk>/delete/', views.media_delete, name='media_delete'),
    path('media/<str:media_id>/toggle-favorite/', views.toggle_favorite, name='toggle_favorite'),
    
    # Favorites
    path('favorites/', views.favorite_list, name='favorite_list'),
    
    # Admin routes
    path('manage/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('manage/users/', views.user_management, name='user_management'),
    path('manage/content/', views.content_management, name='content_management'),
] 