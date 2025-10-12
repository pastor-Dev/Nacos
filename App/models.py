from django.db import models
from django.contrib.auth.models import User



class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE,related_name='profile')
    level = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=100, default="Computer Science")

    def __str__(self):
        return self.user.username




from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys


class UserProfile(models.Model):
    """Extended user profile information"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_profile')
    
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



from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.utils import timezone


class Course(models.Model):
    """Courses/Subjects in the department"""
    code = models.CharField(max_length=20, unique=True, help_text="e.g., CSC201")
    name = models.CharField(max_length=200, help_text="e.g., Introduction to Programming")
    level = models.CharField(max_length=10, choices=[
        ('100', '100 Level'),
        ('200', '200 Level'),
        ('300', '300 Level'),
        ('400', '400 Level'),
        ('500', '500 Level'),
    ])
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['level', 'code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class ClassSchedule(models.Model):
    """Scheduled classes with Zoom links"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='classes')
    title = models.CharField(max_length=200, help_text="e.g., Week 5: Data Structures")
    description = models.TextField(blank=True, help_text="What will be covered in this class")
    
    # Schedule
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    # Zoom/Meeting Link
    meeting_link = models.URLField(help_text="Zoom, Google Meet, or any meeting link")
    meeting_password = models.CharField(max_length=50, blank=True, help_text="Optional meeting password")
    
    # Metadata
    lecturer = models.CharField(max_length=200, help_text="Lecturer name")
    is_completed = models.BooleanField(default=False, help_text="Mark as completed after class")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date', '-start_time']
        verbose_name = "Class Schedule"
        verbose_name_plural = "Class Schedules"
    
    def __str__(self):
        return f"{self.course.code} - {self.title} ({self.date})"
    
    def is_upcoming(self):
        """Check if class is in the future"""
        now = timezone.now()
        class_datetime = timezone.make_aware(
            timezone.datetime.combine(self.date, self.start_time)
        )
        return class_datetime > now
    
    def is_today(self):
        """Check if class is today"""
        return self.date == timezone.now().date()
    
    def get_status(self):
        """Get class status"""
        if self.is_completed:
            return 'completed'
        elif self.is_today():
            return 'today'
        elif self.is_upcoming():
            return 'upcoming'
        else:
            return 'past'


class ResourceCategory(models.Model):
    """Categories for resources (Past Questions, Handouts, etc.)"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='📄', help_text="Emoji icon")
    order = models.IntegerField(default=0, help_text="Display order")
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = "Resource Categories"
    
    def __str__(self):
        return self.name


class Resource(models.Model):
    """Learning resources (PDFs, documents, etc.)"""
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Categorization
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='resources')
    category = models.ForeignKey(ResourceCategory, on_delete=models.SET_NULL, null=True, related_name='resources')
    
    # File
    file = models.FileField(
        upload_to='resources/%Y/%m/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt', 'zip'])],
        help_text="Allowed: PDF, DOC, DOCX, PPT, PPTX, TXT, ZIP"
    )
    file_size = models.IntegerField(default=0, help_text="File size in bytes")
    
    # Metadata
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    upload_date = models.DateTimeField(auto_now_add=True)
    download_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-upload_date']
    
    def __str__(self):
        return f"{self.title} ({self.course.code})"
    
    def get_file_extension(self):
        """Get file extension"""
        return self.file.name.split('.')[-1].upper()
    
    def get_file_size_mb(self):
        """Get file size in MB"""
        return round(self.file_size / (1024 * 1024), 2)
    
    def increment_downloads(self):
        """Increment download count"""
        self.download_count += 1
        self.save(update_fields=['download_count'])


class ResourceDownload(models.Model):
    """Track resource downloads"""
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='downloads')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    downloaded_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    
    class Meta:
        ordering = ['-downloaded_at']
    
    def __str__(self):
        return f"{self.user.username} downloaded {self.resource.title}"


class ClassAttendance(models.Model):
    """Track who joined classes (optional)"""
    class_schedule = models.ForeignKey(ClassSchedule, on_delete=models.CASCADE, related_name='attendance')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['class_schedule', 'user']
        ordering = ['-joined_at']
    
    def __str__(self):
        return f"{self.user.username} joined {self.class_schedule.title}"


# Signal to set file size automatically
from django.db.models.signals import pre_save
from django.dispatch import receiver

@receiver(pre_save, sender=Resource)
def set_file_size(sender, instance, **kwargs):
    """Automatically set file size before saving"""
    if instance.file and hasattr(instance.file, 'size'):
        instance.file_size = instance.file.size