from django.db import models
from django.contrib.auth.models import User


#user profile
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    user_photo = models.ImageField(upload_to='profiles/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_organizer = models.BooleanField(default=False)
    organization_name = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"


#environmental activities and events
class Activity(models.Model):
    CATEGORY_CHOICES = [
        ('Tree Planting', 'Tree Planting'),
        ('Recycling', 'Recycling'),
        ('Cleanup', 'Cleanup'),
        ('Awareness', 'Awareness'),
        ('Education', 'Education'),
        ('Other', 'Other'),
    ]

    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Other')
    title = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=200)
    date = models.DateTimeField()
    is_featured = models.BooleanField(default=False, help_text="Mark as featured to show on homepage (staff only)")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.category})"


#photos or videos user uploaded for activities
class Media(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='media')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_media')
    file = models.FileField(upload_to='activity_media/')
    created_at = models.DateTimeField(auto_now_add=True)

    def is_image(self):
        return self.file.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))

    def is_video(self):
        return self.file.name.lower().endswith(('.mp4', '.mov', '.avi', '.mkv'))

    def __str__(self):
        return f"Media for {self.activity.title} by {self.created_by.username}"


#user join activities
class Registration(models.Model):
    STATUS_CHOICES = [
        ('joined', 'Joined'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    joined_activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='registrations')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='registrations')
    joined_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='joined')

    class Meta:
        unique_together = ('joined_activity', 'user')  # prevent duplicate joins

    def __str__(self):
        return f"{self.user.username} joined {self.joined_activity.title} ({self.status})"


class UserHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='history')
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}: {self.action} on {self.timestamp}"


class ContactMessage(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.name} - {self.subject}"


class Rating(models.Model):
    RATING_CHOICES = [
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ]
    
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings')
    rating = models.IntegerField(choices=RATING_CHOICES, blank=True, null=True)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('activity', 'user')
        ordering = ['-created_at']
    
    def __str__(self):
        if self.rating:
            return f"{self.user.username} - {self.rating} stars for {self.activity.title}"
        else:
            return f"{self.user.username} - comment for {self.activity.title}"
