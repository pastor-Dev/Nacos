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