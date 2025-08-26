from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    level = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=100, default="Computer Science")

    def __str__(self):
        return self.user.username
