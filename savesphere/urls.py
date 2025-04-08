from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from savesphere_app.views import home

urlpatterns = [
    path('', home, name='home'),
    path('app/', include('savesphere_app.urls')),
    path('admin/', admin.site.urls),
    # Redirect all auth URLs to Supabase auth
    path('accounts/login/', RedirectView.as_view(url='/app/login/', permanent=True)),
    path('accounts/logout/', RedirectView.as_view(url='/app/logout/', permanent=True)),
    path('accounts/password_reset/', RedirectView.as_view(url='/app/password-reset/', permanent=True)),
    path('accounts/', include('django.contrib.auth.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 