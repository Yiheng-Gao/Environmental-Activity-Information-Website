from django.db import models
from django.contrib.auth.models import User


#user profile
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    user_photo = models.ImageField(upload_to='profiles/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"


#environmental activities and events
class Activity(models.Model):
    CATEGORY_CHOICES = [
        ('Tree Planting', 'Tree Planting'),
        ('Recycling', 'Recycling'),
        ('Cleanup', 'Cleanup'),
        ('Awareness', 'Awareness'),
        ('Other', 'Other'),
    ]

    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Other')
    title = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=200)
    date = models.DateTimeField()
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
