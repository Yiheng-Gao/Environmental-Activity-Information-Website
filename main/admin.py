from django.contrib import admin
from .models import Profile, Activity, Media, Registration

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'description')
    search_fields = ('user__username',)

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'location', 'date', 'created_by')
    list_filter = ('category', 'date')
    search_fields = ('title', 'description', 'location')

@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ('activity', 'created_by', 'file', 'created_at')
    search_fields = ('activity__title', 'created_by__username')

@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ('user', 'joined_activity', 'status', 'joined_at')
    list_filter = ('status',)
    search_fields = ('user__username', 'joined_activity__title')
