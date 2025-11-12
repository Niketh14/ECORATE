# urls.py - Updated
from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('user/home/', views.user_home, name='user_home'),
    path('seller/home/', views.seller_home, name='seller_home'),
    path('admin/home/', views.admin_home, name='admin_home'),

    # User profile and dashboard
    path('user/profile/', views.user_profile, name='user_profile'),
    path('user/dashboard/', views.user_dashboard, name='user_dashboard'),

    # Products
    path('products/', views.product_list, name='product_list'),
    path('products/<int:product_id>/', views.product_detail, name='product_detail'),

    # Reviews
    path('products/<int:product_id>/review/', views.add_review, name='add_review'),

    # User features
    path('favorites/', views.favorites_list, name='favorites'),
    path('history/', views.user_history, name='user_history'),
    path('toggle-favorite/<int:product_id>/', views.toggle_favorite, name='toggle_favorite'),
    path('buy-product/<int:product_id>/', views.buy_product, name='buy_product'),
    
    # Additional pages
    path('about/', views.about_us, name='about'),
    path('contact/', views.contact_us, name='contact'),
    path('faq/', views.faq, name='faq'),
    
    # Password reset
    path('password-reset/', views.password_reset_request, name='password_reset'),
]