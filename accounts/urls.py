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
]
