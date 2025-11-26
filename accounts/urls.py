# urls.py - Updated
from django.urls import path
from . import views
from . import cart_views

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('user/home/', views.user_home, name='user_home'),
    path('seller/home/', views.seller_home, name='seller_home'),
    path('dashboard/admin/', views.admin_home, name='admin_home'),

    # User profile and dashboard
    path('user/profile/', views.user_profile, name='user_profile'),
    path('user/dashboard/', views.user_dashboard, name='user_dashboard'),

    # Products
    path('products/', views.product_list, name='product_list'),
    path('products/<int:product_id>/', views.product_detail, name='product_detail'),
    path('products/search/suggestions/', views.product_search_suggestions, name='product_search_suggestions'),

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
    path('password-reset-confirm/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
    
    # Seller features
    path('seller/add-product/', views.add_product, name='add_product'),
    path('seller/products/', views.seller_products, name='seller_products'),
    
    # Admin features
    path('admin-login/', views.admin_login_view, name='admin_login'),
    path('manage/approvals/', views.admin_approvals, name='admin_approvals'),
    path('manage/approve-product/<int:product_id>/', views.approve_product, name='approve_product'),
    path('manage/products/', views.admin_products, name='admin_products'),
    path('manage/users/', views.admin_users, name='admin_users'),
    path('manage/reviews/', views.admin_reviews, name='admin_reviews'),
    path('manage/categories/', views.admin_categories, name='admin_categories'),
    path('manage/orders/', views.admin_orders, name='admin_orders'),
    
    # Cart and Orders
    path('cart/', cart_views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', cart_views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:cart_id>/', cart_views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', cart_views.checkout, name='checkout'),
    path('orders/', cart_views.user_orders, name='user_orders'),
    path('seller/orders/', cart_views.seller_orders, name='seller_orders'),
    path('seller/orders/<int:order_id>/update/', cart_views.update_order_status, name='update_order_status'),
]