# views.py - Updated with safe field handling
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from django.db import models
from .forms import CustomUserCreationForm, CustomLoginForm, ProfileEditForm, ReviewForm
from .models import CustomUser, Product, Category, Review


def user_home(request):
    if not request.user.is_authenticated or request.user.user_type != 'user':
        return redirect('login')
    
    # Calculate user stats
    from .models import UserHistory, Favorite
    user_reviews = Review.objects.filter(user=request.user)
    user_favorites = Favorite.objects.filter(user=request.user)
    user_history = UserHistory.objects.filter(user=request.user)
    
    return render(request, 'accounts/user_home.html', {
        'user': request.user,
        'reviews_count': user_reviews.count(),
        'favorites_count': user_favorites.count(),
        'products_viewed': user_history.count(),
    })


@login_required
def seller_home(request):
    if request.user.user_type != 'seller':
        messages.error(request, 'Access denied. Seller account required.')
        return redirect('login')
    
    # Get seller's products
    products = Product.objects.filter(created_by=request.user)
    total_reviews = sum(product.reviews.count() for product in products)
    
    return render(request, 'accounts/seller_home.html', {
        'products': products,
        'total_products': products.count(),
        'total_reviews': total_reviews
    })


@login_required
def admin_home(request):
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied. Admin account required.')
        return redirect('login')
    
    # Admin dashboard stats
    from .models import Review
    total_users = CustomUser.objects.count()
    total_products = Product.objects.count()
    total_reviews = Review.objects.count()
    total_categories = Category.objects.count()
    
    return render(request, 'accounts/admin_home.html', {
        'total_users': total_users,
        'total_products': total_products,
        'total_reviews': total_reviews,
        'total_categories': total_categories
    })


def landing_page(request):
    return render(request, 'accounts/landing.html')


def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Account created for {user.username}! You can now log in.')
            return redirect('login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        # Redirect based on existing session
        if request.user.user_type == 'user':
            return redirect('user_home')
        elif request.user.user_type == 'seller':
            return redirect('seller_home')
        elif request.user.user_type == 'admin':
            return redirect('admin_home')

    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')

            # Redirect based on role
            if user.user_type == 'user':
                return redirect('user_home')
            elif user.user_type == 'seller':
                return redirect('seller_home')
            elif user.user_type == 'admin':
                return redirect('admin_home')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = CustomLoginForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    if request.user.is_authenticated:
        messages.info(request, f'You have been logged out, {request.user.username}.')
    logout(request)
    return redirect('landing')


@login_required
def user_profile(request):
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('user_profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProfileEditForm(instance=request.user)

    return render(request, 'accounts/user_profile.html', {
        'form': form,
        'user_obj': request.user,
    })


@login_required
def user_dashboard(request):
    if request.user.user_type != 'user':
        return redirect('login')

    return render(request, 'accounts/user_dashboard.html', {
        'user': request.user
    })


@login_required
def product_list(request):
    products = Product.objects.all().select_related('category')
    categories = Category.objects.all()

    # Advanced filtering
    search_query = request.GET.get('search')
    category_filter = request.GET.get('category')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    min_rating = request.GET.get('min_rating')
    eco_score = request.GET.get('eco_score')

    if search_query:
        products = products.filter(
            models.Q(name__icontains=search_query) |
            models.Q(description__icontains=search_query) |
            models.Q(brand__icontains=search_query)
        )
    
    if category_filter:
        products = products.filter(category_id=category_filter)
    
    if min_price:
        products = products.filter(price__gte=min_price)
    
    if max_price:
        products = products.filter(price__lte=max_price)
    
    if eco_score:
        products = products.filter(sustainability_score__gte=eco_score)

    return render(request, 'accounts/product_list.html', {
        'products': products,
        'categories': categories,
        'search_query': search_query,
        'selected_category': category_filter,
        'min_price': min_price,
        'max_price': max_price,
        'eco_score': eco_score
    })


@login_required
def product_detail(request, product_id):
    from .models import UserHistory, Favorite
    product = get_object_or_404(Product, id=product_id)
    reviews = product.reviews.all().select_related('user').order_by('-created_at')
    
    # Track user history
    UserHistory.objects.get_or_create(
        user=request.user,
        product=product,
        defaults={'viewed_at': timezone.now()}
    )
    
    # Check if favorited
    is_favorited = Favorite.objects.filter(user=request.user, product=product).exists()
    
    return render(request, 'accounts/product_detail.html', {
        'product': product,
        'reviews': reviews,
        'is_favorited': is_favorited
    })


@login_required
def add_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    # Check if user already reviewed this product
    existing_review = product.reviews.filter(user=request.user).first()
    if existing_review:
        messages.warning(request, 'You have already reviewed this product.')
        return redirect('product_detail', product_id=product.id)

    if request.method == 'POST':
        form = ReviewForm(request.POST, request.FILES)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            messages.success(request, 'Your review has been added successfully!')
            return redirect('product_detail', product_id=product.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ReviewForm()

    return render(request, 'accounts/add_review.html', {
        'form': form,
        'product': product
    })


@login_required
def toggle_favorite(request, product_id):
    from .models import Favorite
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        favorite, created = Favorite.objects.get_or_create(
            user=request.user,
            product=product
        )
        
        if not created:
            favorite.delete()
            favorited = False
        else:
            favorited = True
        
        return JsonResponse({'favorited': favorited})
    return JsonResponse({'error': 'Invalid request'})


@login_required
def favorites_list(request):
    from .models import Favorite
    favorites = Favorite.objects.filter(user=request.user).select_related('product')
    return render(request, 'accounts/favorites.html', {'favorites': favorites})


@login_required
def user_history(request):
    from .models import UserHistory
    history = UserHistory.objects.filter(user=request.user).select_related('product')[:20]
    return render(request, 'accounts/history.html', {'history': history})


@login_required
def buy_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        # Process purchase (simplified)
        messages.success(request, f'🎉 Purchase successful! Thank you for buying {product.name}. You will receive an email confirmation shortly.')
        return redirect('product_detail', product_id=product.id)
    
    return render(request, 'accounts/buy_product.html', {'product': product})


def about_us(request):
    return render(request, 'accounts/about.html')


def contact_us(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        # For now, just show success message (email can be configured later)
        messages.success(request, f'Thank you {name}! Your message has been received. We will get back to you soon.')
        return redirect('contact')
    
    return render(request, 'accounts/contact.html')


def faq(request):
    return render(request, 'accounts/faq.html')


def password_reset_request(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = CustomUser.objects.get(email=email)
            # Generate token and send email (simplified)
            messages.success(request, 'Password reset instructions have been sent to your email.')
            return redirect('login')
        except CustomUser.DoesNotExist:
            messages.error(request, 'No account found with this email address.')
    
    return render(request, 'accounts/password_reset.html')