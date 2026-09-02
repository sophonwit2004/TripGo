from django.db import models
from django.contrib.auth.models import User

class Pin(models.Model):
    name = models.CharField(max_length=255)
    province = models.CharField(max_length=100, default='ศรีสะเกษ')
    district = models.CharField(max_length=100, blank=True, default='')
    village = models.CharField(max_length=100, blank=True, default='')
    category = models.CharField(max_length=100, default='พักผ่อนหย่อนใจ')
    description = models.TextField(blank=True, default='')
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    image = models.FileField(upload_to='pins/', null=True, blank=True)
    image_url = models.CharField(max_length=500, blank=True, default='')
    recommended_tags = models.CharField(max_length=255, blank=True, default='📸 จุดถ่ายรูปสวย')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='pins')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class PinLike(models.Model):
    pin = models.ForeignKey(Pin, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pin_likes')
    reaction_emoji = models.CharField(max_length=20, default='❤️')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('pin', 'user')

class PinComment(models.Model):
    pin = models.ForeignKey(Pin, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pin_comments')
    author_name = models.CharField(max_length=100, blank=True, default='')
    text = models.TextField()
    emoji = models.CharField(max_length=20, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

class PinCheckin(models.Model):
    pin = models.ForeignKey(Pin, on_delete=models.CASCADE, related_name='checkins')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pin_checkins')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('pin', 'user')
