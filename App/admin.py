from django.contrib import admin
from django.utils.html import format_html
from .models import Course, ClassSchedule, Resource, ResourceCategory, ResourceDownload, ClassAttendance


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'level', 'resource_count', 'is_active']
    list_filter = ['level', 'is_active']
    search_fields = ['code', 'name']
    list_editable = ['is_active']
    
    def resource_count(self, obj):
        count = obj.resources.count()
        return format_html('<strong>{}</strong> resources', count)
    resource_count.short_description = 'Resources'


@admin.register(ClassSchedule)
class ClassScheduleAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'date', 'start_time', 'lecturer', 'status_badge', 'attendance_count']
    list_filter = ['date', 'course', 'is_completed']
    search_fields = ['title', 'lecturer', 'course__code']
    readonly_fields = ['created_by', 'created_at']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Class Information', {
            'fields': ('course', 'title', 'description', 'lecturer')
        }),
        ('Schedule', {
            'fields': ('date', 'start_time', 'end_time')
        }),
        ('Meeting Details', {
            'fields': ('meeting_link', 'meeting_password')
        }),
        ('Status', {
            'fields': ('is_completed',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating new
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def status_badge(self, obj):
        status = obj.get_status()
        colors = {
            'today': 'green',
            'upcoming': 'blue',
            'past': 'gray',
            'completed': 'purple'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(status, 'gray'),
            status.upper()
        )
    status_badge.short_description = 'Status'
    
    def attendance_count(self, obj):
        count = obj.attendance.count()
        return format_html('<strong>{}</strong> students', count)
    attendance_count.short_description = 'Attendance'


@admin.register(ResourceCategory)
class ResourceCategoryAdmin(admin.ModelAdmin):
    list_display = ['icon', 'name', 'resource_count', 'order']
    list_editable = ['order']
    
    def resource_count(self, obj):
        count = obj.resources.count()
        return format_html('<strong>{}</strong>', count)
    resource_count.short_description = 'Resources'


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'category', 'file_type', 'file_size_display', 'download_count', 'uploaded_by', 'upload_date', 'is_active']
    list_filter = ['category', 'course__level', 'upload_date', 'is_active']
    search_fields = ['title', 'description', 'course__code', 'course__name']
    readonly_fields = ['uploaded_by', 'upload_date', 'download_count', 'file_size']
    list_editable = ['is_active']
    date_hierarchy = 'upload_date'
    
    fieldsets = (
        ('Resource Information', {
            'fields': ('title', 'description', 'course', 'category')
        }),
        ('File', {
            'fields': ('file', 'file_size')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('uploaded_by', 'upload_date', 'download_count'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating new
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)
    
    def file_type(self, obj):
        ext = obj.get_file_extension()
        colors = {
            'PDF': '#dc2626',
            'DOC': '#2563eb',
            'DOCX': '#2563eb',
            'PPT': '#ea580c',
            'PPTX': '#ea580c',
            'ZIP': '#7c3aed'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px; font-weight: bold; font-size: 11px;">{}</span>',
            colors.get(ext, '#6b7280'),
            ext
        )
    file_type.short_description = 'Type'
    
    def file_size_display(self, obj):
        size_mb = obj.get_file_size_mb()
        if size_mb < 1:
            return f"{int(obj.file_size / 1024)} KB"
        return f"{size_mb} MB"
    file_size_display.short_description = 'Size'


@admin.register(ResourceDownload)
class ResourceDownloadAdmin(admin.ModelAdmin):
    list_display = ['user', 'resource', 'downloaded_at', 'ip_address']
    list_filter = ['downloaded_at']
    search_fields = ['user__username', 'resource__title']
    readonly_fields = ['resource', 'user', 'downloaded_at', 'ip_address']
    date_hierarchy = 'downloaded_at'
    
    def has_add_permission(self, request):
        return False


@admin.register(ClassAttendance)
class ClassAttendanceAdmin(admin.ModelAdmin):
    list_display = ['user', 'class_schedule', 'joined_at']
    list_filter = ['joined_at', 'class_schedule__course']
    search_fields = ['user__username', 'class_schedule__title']
    readonly_fields = ['class_schedule', 'user', 'joined_at']
    date_hierarchy = 'joined_at'
    
    def has_add_permission(self, request):
        return False