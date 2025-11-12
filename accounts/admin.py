# admin.py - Updated
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Category, Product, Review


class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type', 'is_staff')
    list_filter = ('user_type', 'is_staff', 'is_superuser')
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('user_type', 'profile_pic', 'bio', 'location', 'website', 'phone_number',
                       'sustainability_interests')
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('user_type', 'email')
        }),
    )


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Category)
admin.site.register(Product)
admin.site.register(Review)

