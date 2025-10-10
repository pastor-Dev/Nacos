from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys


class UserProfile(models.Model):
    """Extended user profile information"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Personal Information
    bio = models.TextField(max_length=500, blank=True, help_text="Tell us about yourself")
    phone = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    
    # Academic Information
    registration_number = models.CharField(max_length=50, blank=True)
    level = models.CharField(max_length=20, blank=True, choices=[
        ('100', '100 Level'),
        ('200', '200 Level'),
        ('300', '300 Level'),
        ('400', '400 Level'),
        ('500', '500 Level'),
    ])
    department = models.CharField(max_length=100, blank=True, default='Computer Science')
    
    # Profile Picture
    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])],
        help_text="Upload image (max 100KB, jpg/png only)"
    )
    
    # Social Links
    twitter = models.URLField(max_length=200, blank=True)
    linkedin = models.URLField(max_length=200, blank=True)
    github = models.URLField(max_length=200, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    def save(self, *args, **kwargs):
        """Compress and resize profile picture before saving"""
        if self.profile_picture:
            # Open the image
            img = Image.open(self.profile_picture)
            
            # Convert to RGB if necessary (for PNG with transparency)
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # Resize image to max 400x400 while maintaining aspect ratio
            max_size = (400, 400)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save to BytesIO object
            output = BytesIO()
            
            # Start with quality 95 and reduce until under 100KB
            quality = 95
            while True:
                output.seek(0)
                output.truncate()
                img.save(output, format='JPEG', quality=quality, optimize=True)
                
                # Check file size
                size = output.tell()
                if size <= 100 * 1024 or quality <= 20:  # 100KB or minimum quality
                    break
                quality -= 5
            
            # Create new InMemoryUploadedFile
            output.seek(0)
            self.profile_picture = InMemoryUploadedFile(
                output, 'ImageField',
                f"{self.profile_picture.name.split('.')[0]}.jpg",
                'image/jpeg',
                sys.getsizeof(output), None
            )
        
        super().save(*args, **kwargs)
    
    def get_profile_picture_url(self):
        """Get profile picture URL or default"""
        if self.profile_picture:
            return self.profile_picture.url
        return '/static/images/default-avatar.png'  # Add a default avatar


class UserPreferences(models.Model):
    """User preferences and settings"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')
    
    # Notification Settings
    email_notifications = models.BooleanField(default=True, help_text="Receive email notifications")
    sms_notifications = models.BooleanField(default=False, help_text="Receive SMS notifications")
    election_reminders = models.BooleanField(default=True, help_text="Get reminders for upcoming elections")
    payment_reminders = models.BooleanField(default=True, help_text="Get reminders for pending payments")
    
    # Privacy Settings
    show_profile_to_members = models.BooleanField(default=True, help_text="Show profile to other members")
    show_email = models.BooleanField(default=False, help_text="Show email on profile")
    show_phone = models.BooleanField(default=False, help_text="Show phone number on profile")
    
    # Theme Preferences
    dark_mode = models.BooleanField(default=False, help_text="Enable dark mode")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Preferences"


class LoginHistory(models.Model):
    """Track user login history for security"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_history')
    ip_address = models.GenericIPAddressField()
    user_agent = models.CharField(max_length=255, blank=True)
    login_time = models.DateTimeField(auto_now_add=True)
    logout_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-login_time']
        verbose_name_plural = "Login Histories"
    
    def __str__(self):
        return f"{self.user.username} - {self.login_time}"


# Signal to create profile and preferences automatically
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create UserProfile and UserPreferences when new user is created"""
    if created:
        UserProfile.objects.get_or_create(user=instance)
        UserPreferences.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save profile when user is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()
    if hasattr(instance, 'preferences'):
        instance.preferences.save()