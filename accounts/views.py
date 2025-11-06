from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from .forms import CustomUserCreationForm, CustomLoginForm
from django.http import HttpResponse

def user_home(request):
    return HttpResponse("Welcome Registered User")

def seller_home(request):
    return HttpResponse("Welcome Registered Seller")

def admin_home(request):
    return HttpResponse("Welcome Admin")

def landing_page(request):
    return render(request, 'accounts/landing.html')

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Redirect based on role
            if user.user_type == 'user':
                return redirect('user_home')
            elif user.user_type == 'seller':
                return redirect('seller_home')
            elif user.user_type == 'admin':
                return redirect('admin_home')
    else:
        form = CustomLoginForm()
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')
