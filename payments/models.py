from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

class PaymentType(models.Model):
    """Different types of payments (dues, events, etc.)"""
    name = models.CharField(max_length=100)
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - ₦{self.amount}"
    
    class Meta:
        ordering = ['-created_at']


class Payment(models.Model):
    """Track all payment transactions"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('abandoned', 'Abandoned'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    payment_type = models.ForeignKey(PaymentType, on_delete=models.SET_NULL, null=True)
    
    # Payment details
    reference = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Gateway response data
    gateway_response = models.JSONField(null=True, blank=True)
    transaction_date = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.reference} - {self.status}"
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['reference']),
            models.Index(fields=['status']),
        ]
    
    def mark_as_success(self, gateway_data=None):
        """Mark payment as successful"""
        self.status = 'success'
        self.transaction_date = timezone.now()
        if gateway_data:
            self.gateway_response = gateway_data
        self.save()
    
    def mark_as_failed(self, gateway_data=None):
        """Mark payment as failed"""
        self.status = 'failed'
        if gateway_data:
            self.gateway_response = gateway_data
        self.save()


class PaymentHistory(models.Model):
    """Audit trail for payment status changes"""
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='history')
    status = models.CharField(max_length=20)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.payment.reference} - {self.status}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Payment Histories"