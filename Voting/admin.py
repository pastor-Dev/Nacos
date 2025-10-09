from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import Election, Position, Candidate, Vote, VoterProfile, VotingSession


@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    list_display = ['title', 'status_badge', 'start_date', 'end_date', 'total_votes', 'show_results']
    list_filter = ['status', 'start_date', 'show_results', 'results_published']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['show_results']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description')
        }),
        ('Schedule', {
            'fields': ('start_date', 'end_date', 'status')
        }),
        ('Results Settings', {
            'fields': ('show_results', 'results_published')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'upcoming': '#FFA500',
            'active': '#28a745',
            'closed': '#6c757d'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def total_votes(self, obj):
        count = Vote.objects.filter(candidate__position__election=obj).count()
        return format_html('<strong>{}</strong>', count)
    total_votes.short_description = 'Total Votes'
    
    actions = ['activate_election', 'close_election', 'publish_results']
    
    def activate_election(self, request, queryset):
        queryset.update(status='active')
    activate_election.short_description = "Activate selected elections"
    
    def close_election(self, request, queryset):
        queryset.update(status='closed')
    close_election.short_description = "Close selected elections"
    
    def publish_results(self, request, queryset):
        queryset.update(results_published=True)
    publish_results.short_description = "Publish results for selected elections"


class CandidateInline(admin.TabularInline):
    model = Candidate
    extra = 1
    fields = ['name', 'registration_number', 'level', 'is_active']


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ['get_position_name', 'election', 'order', 'candidate_count', 'vote_count']
    list_filter = ['election', 'name']
    search_fields = ['name', 'election__title']
    inlines = [CandidateInline]
    
    def get_position_name(self, obj):
        return obj.get_name_display()
    get_position_name.short_description = 'Position'
    
    def candidate_count(self, obj):
        count = obj.candidates.filter(is_active=True).count()
        return format_html('<strong>{}</strong>', count)
    candidate_count.short_description = 'Candidates'
    
    def vote_count(self, obj):
        count = obj.get_total_votes()
        return format_html('<strong>{}</strong>', count)
    vote_count.short_description = 'Votes'


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_position', 'registration_number', 'level', 'vote_count', 'is_active']
    list_filter = ['position__election', 'position__name', 'is_active']
    search_fields = ['name', 'registration_number']
    readonly_fields = ['created_at', 'vote_count']
    list_editable = ['is_active']
    
    fieldsets = (
        ('Candidate Information', {
            'fields': ('position', 'name', 'registration_number', 'level')
        }),
        ('Manifesto', {
            'fields': ('manifesto',)
        }),
        ('Profile Image', {
            'fields': ('profile_image',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Statistics', {
            'fields': ('vote_count', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_position(self, obj):
        return f"{obj.position.get_name_display()} - {obj.position.election.title}"
    get_position.short_description = 'Position'
    
    def vote_count(self, obj):
        count = obj.get_vote_count()
        percentage = obj.get_vote_percentage()
        return format_html(
            '<strong>{}</strong> votes (<span style="color: green;">{:.1f}%</span>)',
            count,
            percentage
        )
    vote_count.short_description = 'Votes'


@admin.register(VoterProfile)
class VoterProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'registration_number', 'level', 'has_paid_dues', 'is_verified', 'vote_status']
    list_filter = ['has_paid_dues', 'is_verified', 'level']
    search_fields = ['user__username', 'registration_number', 'phone']
    readonly_fields = ['created_at']
    list_editable = ['is_verified']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'registration_number', 'phone', 'level')
        }),
        ('Status', {
            'fields': ('has_paid_dues', 'is_verified')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
    
    def vote_status(self, obj):
        voted_count = Vote.objects.filter(voter=obj.user).values('candidate__position__election').distinct().count()
        if voted_count > 0:
            return format_html('<span style="color: green;">✓ Voted in {} election(s)</span>', voted_count)
        return format_html('<span style="color: gray;">Not voted</span>')
    vote_status.short_description = 'Voting Status'
    
    actions = ['verify_voters', 'mark_as_paid']
    
    def verify_voters(self, request, queryset):
        queryset.update(is_verified=True)
    verify_voters.short_description = "Verify selected voters"
    
    def mark_as_paid(self, request, queryset):
        queryset.update(has_paid_dues=True)
    mark_as_paid.short_description = "Mark as paid dues"


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ['voter', 'candidate', 'get_position', 'get_election', 'timestamp']
    list_filter = ['candidate__position__election', 'candidate__position__name', 'timestamp']
    search_fields = ['voter__username', 'candidate__name']
    readonly_fields = ['voter', 'candidate', 'timestamp', 'ip_address']
    date_hierarchy = 'timestamp'
    
    def get_position(self, obj):
        return obj.candidate.position.get_name_display()
    get_position.short_description = 'Position'
    
    def get_election(self, obj):
        return obj.candidate.position.election.title
    get_election.short_description = 'Election'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Only superusers can delete votes
        return request.user.is_superuser


@admin.register(VotingSession)
class VotingSessionAdmin(admin.ModelAdmin):
    list_display = ['voter', 'election', 'started_at', 'completed_at', 'is_completed', 'votes_cast']
    list_filter = ['election', 'is_completed', 'started_at']
    search_fields = ['voter__username', 'election__title']
    readonly_fields = ['voter', 'election', 'started_at', 'completed_at', 'ip_address']
    date_hierarchy = 'started_at'
    
    def votes_cast(self, obj):
        count = Vote.objects.filter(
            voter=obj.voter,
            candidate__position__election=obj.election
        ).count()
        return format_html('<strong>{}</strong>', count)
    votes_cast.short_description = 'Votes Cast'
    
    def has_add_permission(self, request):
        return False