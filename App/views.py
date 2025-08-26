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
