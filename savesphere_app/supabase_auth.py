"""
Supabase authentication for SaveSphere app.
"""

from django.contrib.auth import login, authenticate
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.conf import settings
from savesphere.supabase import get_supabase_client
from .forms import UserRegisterForm, UserLoginForm
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import ValidationError
from .models import UserProfile
from supabase import create_client, Client
import os

supabase = get_supabase_client()

class SupabaseAuthBackend(ModelBackend):
    def authenticate(self, request, email=None, password=None, **kwargs):
        try:
            # Initialize Supabase client
            supabase: Client = create_client(
                os.environ.get('SUPABASE_URL', ''),
                os.environ.get('SUPABASE_KEY', '')
            )
            
            # Sign in with email and password
            auth_response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if auth_response.user:
                # Get or create UserProfile
                user_profile, created = UserProfile.objects.get_or_create(
                    user_id=auth_response.user.id,
                    defaults={
                        'email': email,
                        'role': 'user'  # Default role
                    }
                )
                
                # If this is an admin login attempt, verify admin role
                if user_profile.role == 'admin':
                    # Store session data
                    request.session['user_id'] = auth_response.user.id
                    request.session['access_token'] = auth_response.session.access_token
                    request.session['refresh_token'] = auth_response.session.refresh_token
                    request.session['is_admin'] = True
                    return user_profile
                elif user_profile.role in ['staff', 'user']:
                    # Store session data for regular users
                    request.session['user_id'] = auth_response.user.id
                    request.session['access_token'] = auth_response.session.access_token
                    request.session['refresh_token'] = auth_response.session.refresh_token
                    request.session['is_admin'] = False
                    return user_profile
                
        except Exception as e:
            print(f"Authentication error: {str(e)}")
            return None

    def get_user(self, user_id):
        try:
            return UserProfile.objects.get(user_id=user_id)
        except UserProfile.DoesNotExist:
            return None

def register_view(request):
    """Handle user registration with Supabase Auth."""
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            try:
                # Initialize Supabase client
                supabase: Client = create_client(
                    os.environ.get('SUPABASE_URL', ''),
                    os.environ.get('SUPABASE_KEY', '')
                )
                
                # Check if user exists in Supabase
                try:
                    auth_response = supabase.auth.sign_in_with_password({
                        "email": email,
                        "password": password
                    })
                    # If sign in succeeds, user exists in Supabase
                    messages.error(request, "This email is already registered. Please try logging in or use password reset.")
                    return redirect('savesphere_app:login')
                except Exception as e:
                    # User doesn't exist in Supabase, proceed with registration
                    pass
                
                # Clean up any orphaned UserProfile records
                try:
                    orphaned_profiles = UserProfile.objects.filter(email=email)
                    if orphaned_profiles.exists():
                        orphaned_profiles.delete()
                except Exception as e:
                    print(f"Error cleaning up orphaned profiles: {str(e)}")
                
                # Create user in Supabase with custom redirect URL
                redirect_url = request.build_absolute_uri('/app/verify/')
                auth_response = supabase.auth.sign_up({
                    "email": email,
                    "password": password,
                    "options": {
                        "emailRedirectTo": redirect_url
                    }
                })
                
                if auth_response.user:
                    # Create UserProfile
                    UserProfile.objects.create(
                        user_id=auth_response.user.id,
                        email=email
                    )
                    
                    messages.success(request, "Registration successful! Please check your email to verify your account.")
                    return redirect('savesphere_app:login')
                    
            except Exception as e:
                messages.error(request, f"Registration failed: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = UserRegisterForm()
    
    return render(request, 'registration/register.html', {'form': form})

def login_view(request):
    """Handle user login with Supabase Auth."""
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            login_type = request.POST.get('login_type', 'user')
            
            try:
                # Initialize Supabase client
                supabase: Client = create_client(
                    os.environ.get('SUPABASE_URL', ''),
                    os.environ.get('SUPABASE_KEY', '')
                )
                
                # Sign in with email and password
                auth_response = supabase.auth.sign_in_with_password({
                    "email": email,
                    "password": password
                })
                
                if auth_response.user:
                    # Get or create UserProfile
                    user_profile, created = UserProfile.objects.get_or_create(
                        user_id=auth_response.user.id,
                        defaults={
                            'email': email,
                            'role': 'user'
                        }
                    )
                    
                    # Store session data
                    request.session['user_id'] = auth_response.user.id
                    request.session['access_token'] = auth_response.session.access_token
                    request.session['refresh_token'] = auth_response.session.refresh_token
                    
                    # Check if this is an admin login attempt
                    if login_type == 'admin':
                        if user_profile.role != 'admin':
                            messages.error(request, "You don't have admin privileges.")
                            return redirect('savesphere_app:login')
                        request.session['is_admin'] = True
                        messages.success(request, "Admin login successful!")
                        return redirect('savesphere_app:admin_dashboard')
                    else:
                        request.session['is_admin'] = False
                        messages.success(request, "Login successful!")
                        return redirect('savesphere_app:dashboard')
                
            except Exception as e:
                messages.error(request, f"Login failed: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = UserLoginForm()
    
    return render(request, 'registration/login.html', {'form': form})

def logout_view(request):
    """Handle user logout with Supabase Auth."""
    try:
        # Initialize Supabase client
        supabase: Client = create_client(
            os.environ.get('SUPABASE_URL', ''),
            os.environ.get('SUPABASE_KEY', '')
        )
        
        # Get the access token from session
        access_token = request.session.get('access_token')
        if access_token:
            # Sign out from Supabase using the session
            supabase.auth.sign_out()
        
        # Clear all session data
        request.session.flush()
        
        messages.success(request, "You have been logged out successfully.")
    except Exception as e:
        # Even if Supabase logout fails, we still want to clear the session
        request.session.flush()
        messages.success(request, "You have been logged out successfully.")
    
    return redirect('savesphere_app:login')

def password_reset_request(request):
    """Handle password reset request."""
    if request.method == 'POST':
        email = request.POST.get('email')
        
        try:
            # Initialize Supabase client
            supabase: Client = create_client(
                os.environ.get('SUPABASE_URL', ''),
                os.environ.get('SUPABASE_KEY', '')
            )
            
            # Send password reset email with custom redirect URL
            redirect_url = request.build_absolute_uri('/app/password-reset/')
            supabase.auth.reset_password_for_email(email, {
                'redirectTo': redirect_url
            })
            messages.success(request, "Password reset email sent")
            
        except Exception as e:
            messages.error(request, f"Password reset failed: {str(e)}")
    
    return render(request, 'registration/password_reset.html')

def password_reset_confirm(request, token):
    """Handle password reset confirmation."""
    if request.method == 'POST':
        password = request.POST.get('password')
        
        try:
            # Initialize Supabase client
            supabase: Client = create_client(
                os.environ.get('SUPABASE_URL', ''),
                os.environ.get('SUPABASE_KEY', '')
            )
            
            # Update password with token
            supabase.auth.update_user({
                "password": password
            }, token)
            
            messages.success(request, "Password updated successfully")
            return redirect('savesphere_app:login')
            
        except Exception as e:
            messages.error(request, f"Password update failed: {str(e)}")
    
    return render(request, 'registration/password_reset_confirm.html') 