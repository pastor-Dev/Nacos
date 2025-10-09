from django.contrib import admin
from django.utils.html import format_html
from .models import PaymentType, Payment, PaymentHistory

@admin.register(PaymentType)
class PaymentTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'amount', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['is_active']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'amount')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


class PaymentHistoryInline(admin.TabularInline):
    model = PaymentHistory
    extra = 0
    readonly_fields = ['status', 'note', 'created_at']
    can_delete = False


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['reference', 'user', 'payment_type', 'amount', 'status_badge', 'created_at']
    list_filter = ['status', 'created_at', 'payment_type']
    search_fields = ['reference', 'user__username', 'user__email', 'email']
    readonly_fields = ['reference', 'created_at', 'updated_at', 'gateway_response']
    inlines = [PaymentHistoryInline]
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'email', 'phone')
        }),
        ('Payment Details', {
            'fields': ('payment_type', 'amount', 'reference', 'status')
        }),
        ('Gateway Response', {
            'fields': ('gateway_response', 'transaction_date'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'success': 'green',
            'pending': 'orange',
            'failed': 'red',
            'abandoned': 'gray'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.status.upper()
        )
    status_badge.short_description = 'Status'
    
    def has_add_permission(self, request):
        # Prevent manual creation of payments through admin
        return False


@admin.register(PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = ['payment', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['payment__reference', 'note']
    readonly_fields = ['payment', 'status', 'note', 'created_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False