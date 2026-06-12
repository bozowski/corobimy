from django.conf import settings
from django.db import models

CATEGORY_CHOICES = [
    ('family', 'Families'),
    ('couples', 'Couples'),
    ('sport', 'Sport'),
    ('culture', 'Culture'),
]


class Attraction(models.Model):
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class UserSavedAttraction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_attractions')
    attraction = models.ForeignKey(Attraction, on_delete=models.CASCADE, related_name='saves')
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('user', 'attraction')]
        ordering = ['-saved_at']

    def __str__(self):
        return f"{self.user} → {self.attraction}"
