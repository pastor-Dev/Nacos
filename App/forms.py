from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

# The SignUpForm handles user registration and password hashing.
# It inherits from Django's built-in UserCreationForm for security.
class SignUpForm(UserCreationForm):
    # Additional fields can be added here if needed,
    # but for a basic registration, UserCreationForm is sufficient.
    class Meta:
        model = User
        fields = ['username', 'email']

    # Custom validation for the form, for example to add email and password validation
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


# The SignInForm is for user login. It's a simple form
# since Django's `authenticate` function handles the password check.
class SignInForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={'placeholder': 'Enter your username'}
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={'placeholder': 'Enter your password'}
        )
    )

