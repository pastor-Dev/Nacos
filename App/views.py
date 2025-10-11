from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import SignUpForm, SignInForm
from django.contrib.auth.decorators import login_required


def signin_view(request):
    """Handles login (landing page)."""
    if request.user.is_authenticated:
        return redirect('dashboard')  # Already logged in

    form = SignInForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password']
        )
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'index.html', {'form': form})


def signup_view(request):
    """Handles user registration."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = SignUpForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Account created successfully! Please sign in.")
        return redirect('signin')

    return render(request, 'signup.html', {'form': form})


@login_required(login_url='signin')
def dashboard(request):
    """Dashboard – accessible only to logged-in users."""
    return render(request, 'dashboard.html')


def logout_view(request):
    """Logs out the user and redirects to sign-in."""
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('signin')


def payment_view(request):
    """
    Renders the custom payment processing page.
    This page contains the HTML/JS logic for the simulated payment flow.
    """
    # You can pass context here if needed, but for now, we just render the page.
    return render(request, 'payment_page.html', {})



from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

@login_required
def logout_view(request):
    """Logout user from Django session"""
    logout(request)
    return redirect('signin')  # Change 'login' to your login page URL name

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.core.files.base import ContentFile
from .models import UserProfile, UserPreferences, LoginHistory
import base64


def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@login_required
def profile_view(request):
    """Display user profile"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    preferences, created = UserPreferences.objects.get_or_create(user=request.user)
    
    # Get recent login history
    login_history = LoginHistory.objects.filter(user=request.user)[:5]
    
    # Get user statistics
    from payments.models import Payment
    total_payments = Payment.objects.filter(user=request.user, status='success').count()
    
    try:
        from voting.models import Vote
        total_votes = Vote.objects.filter(voter=request.user).values('candidate__position__election').distinct().count()
    except:
        total_votes = 0
    
    context = {
        'profile': profile,
        'preferences': preferences,
        'login_history': login_history,
        'total_payments': total_payments,
        'total_votes': total_votes,
    }
    return render(request, 'profile/profile_view.html', context)


@login_required
def edit_profile(request):
    """Edit user profile"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Update user basic info
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.email = request.POST.get('email', '')
        request.user.save()
        
        # Update profile info
        profile.bio = request.POST.get('bio', '')
        profile.phone = request.POST.get('phone', '')
        profile.level = request.POST.get('level', '')
        profile.registration_number = request.POST.get('registration_number', '')
        
        # Social links
        profile.twitter = request.POST.get('twitter', '')
        profile.linkedin = request.POST.get('linkedin', '')
        profile.github = request.POST.get('github', '')
        
        # Handle profile picture upload
        if request.FILES.get('profile_picture'):
            profile.profile_picture = request.FILES['profile_picture']
        
        # Handle base64 image from webcam
        if request.POST.get('webcam_image'):
            try:
                format, imgstr = request.POST.get('webcam_image').split(';base64,')
                ext = format.split('/')[-1]
                data = ContentFile(base64.b64decode(imgstr), name=f'webcam_{request.user.id}.{ext}')
                profile.profile_picture = data
            except Exception as e:
                messages.error(request, f'Failed to save webcam image: {str(e)}')
        
        try:
            profile.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile_view')
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
    
    context = {
        'profile': profile,
    }
    return render(request, 'profile/edit_profile.html', context)


@login_required
def edit_preferences(request):
    """Edit user preferences"""
    preferences, created = UserPreferences.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Notification settings
        preferences.email_notifications = request.POST.get('email_notifications') == 'on'
        preferences.sms_notifications = request.POST.get('sms_notifications') == 'on'
        preferences.election_reminders = request.POST.get('election_reminders') == 'on'
        preferences.payment_reminders = request.POST.get('payment_reminders') == 'on'
        
        # Privacy settings
        preferences.show_profile_to_members = request.POST.get('show_profile_to_members') == 'on'
        preferences.show_email = request.POST.get('show_email') == 'on'
        preferences.show_phone = request.POST.get('show_phone') == 'on'
        
        # Theme
        preferences.dark_mode = request.POST.get('dark_mode') == 'on'
        
        preferences.save()
        messages.success(request, 'Preferences updated successfully!')
        return redirect('profile_view')
    
    context = {
        'preferences': preferences,
    }
    return render(request, 'profile/edit_preferences.html', context)


@login_required
def change_password(request):
    """Change user password"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep user logged in
            messages.success(request, 'Password changed successfully!')
            return redirect('profile_view')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = PasswordChangeForm(request.user)
    
    context = {
        'form': form,
    }
    return render(request, 'profile/change_password.html', context)


@login_required
def delete_account(request):
    """Delete user account"""
    if request.method == 'POST':
        password = request.POST.get('password')
        confirm = request.POST.get('confirm_delete')
        
        if confirm == 'DELETE' and request.user.check_password(password):
            # Log out user
            from django.contrib.auth import logout
            user = request.user
            logout(request)
            
            # Delete user account
            user.delete()
            
            messages.success(request, 'Your account has been deleted successfully.')
            return redirect('login')
        else:
            messages.error(request, 'Invalid password or confirmation text.')
    
    return render(request, 'profile/delete_account.html')


@login_required
def activity_log(request):
    """View user activity log"""
    # Login history
    login_history = LoginHistory.objects.filter(user=request.user)[:20]
    
    # Payment history
    from payments.models import Payment
    payments = Payment.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    # Voting history
    try:
        from voting.models import Vote
        votes = Vote.objects.filter(voter=request.user).select_related('candidate', 'candidate__position').order_by('-timestamp')[:10]
    except:
        votes = []
    
    context = {
        'login_history': login_history,
        'payments': payments,
        'votes': votes,
    }
    return render(request, 'profile/activity_log.html', context)


# Helper function to log user login
def log_user_login(request, user):
    """Log user login for security tracking"""
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    LoginHistory.objects.create(
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
        is_active=True
    )