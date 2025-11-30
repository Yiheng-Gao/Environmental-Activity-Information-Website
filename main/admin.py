from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Profile, Activity, Media, Registration

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = ('is_organizer', 'organization_name', 'user_photo', 'description')
    help_text = 'Uncheck "Is Organizer" to downgrade an organizer to a regular member.'

class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_organizer', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    
    def is_organizer(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.is_organizer
        return False
    is_organizer.boolean = True
    is_organizer.short_description = 'Organizer'

admin.site.unregister(User)
admin.site.register(User, UserAdmin)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_organizer', 'organization_name', 'description')
    list_filter = ('is_organizer',)
    search_fields = ('user__username', 'organization_name')
    fields = ('user', 'is_organizer', 'organization_name', 'user_photo', 'description')
    actions = ['downgrade_to_regular', 'upgrade_to_organizer']
    
    def downgrade_to_regular(self, request, queryset):
        updated = queryset.update(is_organizer=False, organization_name='')
        self.message_user(request, f'{updated} user(s) downgraded to regular member(s).')
    downgrade_to_regular.short_description = 'Downgrade selected organizers to regular members'
    
    def upgrade_to_organizer(self, request, queryset):
        count = 0
        for profile in queryset:
            if not profile.is_organizer:
                profile.is_organizer = True
                if not profile.organization_name:
                    profile.organization_name = f"Organization for {profile.user.username}"
                profile.save()
                count += 1
        self.message_user(request, f'{count} user(s) upgraded to organizer(s).')
    upgrade_to_organizer.short_description = 'Upgrade selected users to organizers'

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'location', 'date', 'created_by', 'is_official')
    list_filter = ('category', 'date', 'created_by__profile__is_organizer')
    search_fields = ('title', 'description', 'location', 'created_by__username')
    
    def is_official(self, obj):
        if hasattr(obj.created_by, 'profile'):
            return obj.created_by.profile.is_organizer
        return False
    is_official.boolean = True
    is_official.short_description = 'Official'

@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ('activity', 'created_by', 'file', 'created_at')
    search_fields = ('activity__title', 'created_by__username')

@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ('user', 'joined_activity', 'status', 'joined_at')
    list_filter = ('status',)
    search_fields = ('user__username', 'joined_activity__title')
