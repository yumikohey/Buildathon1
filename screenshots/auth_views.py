from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.http import JsonResponse
from .models import Screenshot


def register_view(request):
    """User registration view."""
    if request.user.is_authenticated:
        return redirect('screenshots:home')
    
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                username = form.cleaned_data.get('username')
                messages.success(request, f'Account created for {username}! You can now log in.')
                return redirect('screenshots:login')
            except IntegrityError:
                messages.error(request, 'Username already exists. Please choose a different username.')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})


def login_view(request):
    """User login view."""
    if request.user.is_authenticated:
        return redirect('screenshots:home')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                next_url = request.GET.get('next')
                if next_url and next_url.startswith('/'):
                    # If next_url is a valid URL path, redirect to it
                    return redirect(next_url)
                else:
                    # Default redirect to home
                    return redirect('screenshots:home')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    
    return render(request, 'registration/login.html', {'form': form})


@login_required
def logout_view(request):
    """User logout view."""
    username = request.user.username
    logout(request)
    messages.success(request, f'You have been logged out successfully, {username}!')
    return redirect('screenshots:login')


@login_required
def profile_view(request):
    """User profile view showing user's screenshots and statistics."""
    user_screenshots = Screenshot.objects.filter(user=request.user)
    
    # Calculate statistics
    total_screenshots = user_screenshots.count()
    processed_screenshots = user_screenshots.filter(processing_status='completed').count()
    pending_screenshots = user_screenshots.filter(processing_status='pending').count()
    failed_screenshots = user_screenshots.filter(processing_status='failed').count()
    
    # Calculate total file size
    total_size_bytes = sum(screenshot.file_size for screenshot in user_screenshots)
    total_size_mb = round(total_size_bytes / (1024 * 1024), 2)
    
    context = {
        'user': request.user,
        'total_screenshots': total_screenshots,
        'processed_screenshots': processed_screenshots,
        'pending_screenshots': pending_screenshots,
        'failed_screenshots': failed_screenshots,
        'total_size_mb': total_size_mb,
        'recent_screenshots': user_screenshots[:5],  # Show 5 most recent
    }
    
    return render(request, 'registration/profile.html', context)


@login_required
def delete_account_view(request):
    """Delete user account and all associated screenshots."""
    if request.method == 'POST':
        user = request.user
        username = user.username
        
        # Delete all user's screenshots (files will be deleted by Django)
        Screenshot.objects.filter(user=user).delete()
        
        # Delete the user account
        user.delete()
        
        messages.success(request, f'Account {username} and all associated data have been deleted.')
        return redirect('screenshots:login')
    
    return render(request, 'screenshots/auth/delete_account.html')