# models.py - Safe version
from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    USER_TYPES = (
        ('user', 'Registered User'),
        ('seller', 'Registered Seller'),
        ('admin', 'Admin'),
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPES, default='user')
    profile_pic = models.ImageField(upload_to='profile_pics/', default='profile_pics/default.jpg', blank=True)

    # Add new fields with default values or allow blank
    bio = models.TextField(max_length=500, blank=True, default='')
    location = models.CharField(max_length=100, blank=True, default='')
    website = models.URLField(blank=True, default='')
    phone_number = models.CharField(max_length=15, blank=True, default='')

    # Environmental preferences
    sustainability_interests = models.TextField(
        blank=True,
        default='',
        help_text="Comma-separated list of sustainability interests"
    )

    def __str__(self):
        return f"{self.username} ({self.user_type})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    brand = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sustainability_score = models.IntegerField(default=0, help_text="1-10 scale")
    eco_certifications = models.CharField(max_length=200, blank=True)
    image = models.ImageField(upload_to='products/', default='products/default.jpg')
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Review(models.Model):
    RATING_CHOICES = [
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField()
    image = models.ImageField(upload_to='review_images/', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['product', 'user']  # One review per user per product

    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.rating} stars)"


class Favorite(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'product']

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"


class UserHistory(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-viewed_at']

    def __str__(self):
        return f"{self.user.username} viewed {self.product.name}"