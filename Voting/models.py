from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
import re

class Election(models.Model):
    """Represents an election period"""
    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('active', 'Active'),
        ('closed', 'Closed'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    show_results = models.BooleanField(default=False, help_text="Show live results during voting")
    results_published = models.BooleanField(default=False, help_text="Publish final results")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
    
    def is_active(self):
        """Check if election is currently active"""
        now = timezone.now()
        return self.status == 'active' and self.start_date <= now <= self.end_date
    
    def can_vote(self):
        """Check if users can currently vote"""
        return self.is_active()
    
    def auto_update_status(self):
        """Automatically update election status based on dates"""
        now = timezone.now()
        if now < self.start_date:
            self.status = 'upcoming'
        elif self.start_date <= now <= self.end_date:
            self.status = 'active'
        else:
            self.status = 'closed'
        self.save()


class Position(models.Model):
    """Electoral positions to vote for"""
    POSITION_CHOICES = [
        ('president', 'President'),
        ('vice_president', 'Vice President'),
        ('social_director', 'Social Director'),
        ('pro_1', 'PRO 1'),
        ('pro_2', 'PRO 2'),
        ('sport_director', 'Sport Director'),
        ('software_director', 'Software Director'),
        ('auditor', 'Auditor'),
        ('sec_general', 'Secretary General'),
        ('treasurer', 'Treasurer'),
        ('financial_sec', 'Financial Secretary'),
        ('senator', 'Senator'),
    ]
    
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='positions')
    name = models.CharField(max_length=50, choices=POSITION_CHOICES)
    order = models.IntegerField(default=0, help_text="Display order on ballot")
    
    class Meta:
        ordering = ['order', 'name']
        unique_together = ['election', 'name']
    
    def __str__(self):
        return f"{self.get_name_display()} - {self.election.title}"
    
    def get_candidates(self):
        """Get all candidates for this position"""
        return self.candidates.filter(is_active=True)
    
    def get_total_votes(self):
        """Get total votes cast for this position"""
        return Vote.objects.filter(candidate__position=self).count()



from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator

class Candidate(models.Model):
    """Election candidates - ENHANCED VERSION"""
    position = models.ForeignKey('Position', on_delete=models.CASCADE, related_name='candidates')
    name = models.CharField(max_length=200)
    registration_number = models.CharField(max_length=50)
    level = models.CharField(max_length=20, blank=True)
    manifesto = models.TextField(help_text="Candidate's manifesto/objectives")
    bio = models.TextField(blank=True, help_text="Short biography (optional)")
    profile_image = models.ImageField(
        upload_to='candidates/profiles/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])],
        help_text="Profile photo"
    )
    campaign_poster = models.ImageField(
        upload_to='candidates/posters/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])],
        help_text="Campaign poster/banner"
    )
    
    # Additional Info (NEW)
    slogan = models.CharField(max_length=200, blank=True, help_text="Campaign slogan")
    achievements = models.TextField(blank=True, help_text="Past achievements and qualifications")
    
    # Social Media (NEW)
    twitter = models.URLField(blank=True, max_length=200)
    linkedin = models.URLField(blank=True, max_length=200)
    instagram = models.URLField(blank=True, max_length=200)
    facebook = models.URLField(blank=True, max_length=200)
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Stats (NEW)
    profile_views = models.IntegerField(default=0, help_text="Number of profile views")
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} - {self.position.get_name_display()}"
    
    def get_vote_count(self):
        """Get total votes for this candidate"""
        return self.votes.count()
    
    def get_vote_percentage(self):
        """Get percentage of votes"""
        total = self.position.get_total_votes()
        if total == 0:
            return 0
        return round((self.get_vote_count() / total) * 100, 2)
    
    def increment_profile_views(self):
        """Increment profile view count"""
        self.profile_views += 1
        self.save(update_fields=['profile_views'])
    
    def get_profile_image_url(self):
        """Get profile image URL or placeholder"""
        if self.profile_image:
            return self.profile_image.url
        return '/static/images/default-candidate.png'
    
    def has_social_media(self):
        """Check if candidate has any social media links"""
        return any([self.twitter, self.linkedin, self.instagram, self.facebook])


class VoterProfile(models.Model):
    """Extended voter information"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='voter_profile')
    registration_number = models.CharField(max_length=50, unique=True)
    phone = models.CharField(max_length=20, blank=True)
    level = models.CharField(max_length=20, blank=True)
    has_paid_dues = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False, help_text="Admin verified registration")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.registration_number}"
    
    def clean(self):
        """Validate registration number format"""
        reg_num = self.registration_number.strip()
        
        # Pattern 1: 22U/360016
        pattern1 = r'^\d{2}[A-Z]/\d{6}$'
        # Pattern 2: FSC/22/360016
        pattern2 = r'^[A-Z]{2,4}/\d{2}/\d{6}$'
        
        if not (re.match(pattern1, reg_num) or re.match(pattern2, reg_num)):
            raise ValidationError(
                'Invalid registration number format. Expected formats: "22U/360016" or "FSC/22/360016"'
            )
    
    def can_vote(self, election):
        """Check if voter is eligible to vote in an election"""
        return (
            self.has_paid_dues and 
            self.is_verified and 
            not self.has_voted_in_election(election)
        )
    
    def has_voted_in_election(self, election):
        """Check if user has voted in this election"""
        return Vote.objects.filter(
            voter=self.user,
            candidate__position__election=election
        ).exists()


class Vote(models.Model):
    """Individual votes cast"""
    voter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='votes')
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='votes')
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    
    class Meta:
        unique_together = ['voter', 'candidate']
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['voter', 'candidate']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.voter.username} voted for {self.candidate.name}"
    
    def save(self, *args, **kwargs):
        """Ensure voter hasn't already voted for this position"""
        position = self.candidate.position
        election = position.election
        
        # Check if user has already voted for this position
        existing_vote = Vote.objects.filter(
            voter=self.voter,
            candidate__position=position
        ).exclude(pk=self.pk).exists()
        
        if existing_vote:
            raise ValidationError(
                f"You have already voted for {position.get_name_display()}"
            )
        
        super().save(*args, **kwargs)


class VotingSession(models.Model):
    """Track voting sessions for audit trail"""
    voter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='voting_sessions')
    election = models.ForeignKey(Election, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.voter.username} - {self.election.title}"
    
    def mark_completed(self):
        """Mark voting session as completed"""
        self.is_completed = True
        self.completed_at = timezone.now()
        self.save()