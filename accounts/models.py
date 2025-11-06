from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    USER_TYPES = (
        ('user', 'Registered User'),
        ('seller', 'Registered Seller'),
        ('admin', 'Admin'),
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPES, default='user')

    def __str__(self):
        return f"{self.username} ({self.user_type})"
