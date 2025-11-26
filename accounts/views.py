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
from django.contrib.auth import update_session_auth_hash
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from django.db import models
from .forms import CustomUserCreationForm, CustomLoginForm, ProfileEditForm, ReviewForm, ProductForm
from .models import CustomUser, Product, Category, Review, ProductImage, Cart, Order


def user_home(request):
    if not request.user.is_authenticated or request.user.user_type != 'user':
        return redirect('login')
    
    # Calculate user stats
    from .models import UserHistory, Favorite
    user_reviews = Review.objects.filter(user=request.user)
    user_favorites = Favorite.objects.filter(user=request.user)
    user_history = UserHistory.objects.filter(user=request.user)
    cart_count = Cart.objects.filter(user=request.user).count()
    
    return render(request, 'accounts/user_home.html', {
        'user': request.user,
        'reviews_count': user_reviews.count(),
        'favorites_count': user_favorites.count(),
        'products_viewed': user_history.count(),
        'cart_count': cart_count,
    })


@login_required
def seller_home(request):
    if request.user.user_type != 'seller':
        messages.error(request, 'Access denied. Seller account required.')
        return redirect('login')
    
    # Get seller's products
    products = Product.objects.filter(created_by=request.user)
    total_reviews = sum(product.reviews.count() for product in products)
    
    # Get order statistics
    orders = Order.objects.filter(seller=request.user)
    pending_orders = orders.filter(status='pending').count()
    total_orders = orders.count()
    
    return render(request, 'accounts/seller_home.html', {
        'products': products,
        'total_products': products.count(),
        'total_reviews': total_reviews,
        'pending_orders': pending_orders,
        'total_orders': total_orders
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
    pending_approvals = Product.objects.filter(status='pending').count()
    
    return render(request, 'accounts/admin_home.html', {
        'total_users': total_users,
        'total_products': total_products,
        'total_reviews': total_reviews,
        'total_categories': total_categories,
        'pending_approvals': pending_approvals
    })


def landing_page(request):
    # Show home page for everyone, including logged-in users
    products = Product.objects.filter(status='approved').select_related('category').prefetch_related('additional_images')[:12]  # Show first 12 approved products
    
    # Process image indices for each product
    for product in products:
        img_param = f'img_{product.id}'
        current_index = request.GET.get(img_param, '0')
        try:
            product.current_image_index = int(current_index)
            # Ensure index is within bounds
            max_index = product.additional_images.count() - 1
            if max_index >= 0:
                product.current_image_index = max(0, min(product.current_image_index, max_index))
            else:
                product.current_image_index = 0
        except (ValueError, TypeError):
            product.current_image_index = 0
    
    return render(request, 'accounts/landing.html', {
        'products': products,
        'user': request.user if request.user.is_authenticated else None
    })


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


def product_list(request):
    # Allow both authenticated and anonymous users to search products
    if request.user.is_authenticated:
        # Show only seller's products if user is a seller
        if request.user.user_type == 'seller':
            products = Product.objects.filter(created_by=request.user).select_related('category').prefetch_related('additional_images')
        else:
            products = Product.objects.filter(status='approved').select_related('category').prefetch_related('additional_images')
    else:
        # Anonymous users can only see approved products
        products = Product.objects.filter(status='approved').select_related('category').prefetch_related('additional_images')
    
    categories = Category.objects.all()

    # Advanced filtering
    search_query = request.GET.get('search', '').strip()
    category_filter = request.GET.get('category', '').strip()
    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()
    eco_score = request.GET.get('eco_score', '').strip()

    if search_query:
        products = products.filter(
            models.Q(name__icontains=search_query) |
            models.Q(description__icontains=search_query) |
            models.Q(brand__icontains=search_query)
        )
    
    if category_filter:
        try:
            products = products.filter(category_id=int(category_filter))
        except (ValueError, TypeError):
            pass
    
    if min_price:
        try:
            products = products.filter(price__gte=float(min_price))
        except (ValueError, TypeError):
            pass
    
    if max_price:
        try:
            products = products.filter(price__lte=float(max_price))
        except (ValueError, TypeError):
            pass
    
    if eco_score:
        try:
            products = products.filter(sustainability_score__gte=int(eco_score))
        except (ValueError, TypeError):
            pass

    # Sorting functionality - sort by product name field (not brand)
    # Product model has: name (product name) and brand (brand name)
    # We sort by 'name' which is the product name field
    from django.db.models.functions import Lower
    sort_by = request.GET.get('sort', '').strip()
    
    # Apply sorting based on user selection
    if sort_by == 'name_asc':
        # Sort by product name A to Z (case-insensitive)
        products = products.annotate(name_lower=Lower('name')).order_by('name_lower', 'id')
    elif sort_by == 'name_desc':
        # Sort by product name Z to A (case-insensitive)
        products = products.annotate(name_lower=Lower('name')).order_by('-name_lower', 'id')
    elif not sort_by or sort_by == '':
        # Default sorting - newest first (by creation date, most recent first)
        products = products.order_by('-created_at', '-id')
    else:
        # Fallback to default if invalid sort value
        products = products.order_by('-created_at', '-id')

    # Process image indices for each product
    for product in products:
        img_param = f'img_{product.id}'
        current_index = request.GET.get(img_param, '0')
        try:
            product.current_image_index = int(current_index)
        except (ValueError, TypeError):
            product.current_image_index = 0

    return render(request, 'accounts/product_list.html', {
        'products': products,
        'categories': categories,
        'search_query': search_query,
        'selected_category': category_filter,
        'min_price': min_price,
        'max_price': max_price,
        'eco_score': eco_score,
        'sort_by': sort_by
    })


def product_search_suggestions(request):
    """API endpoint for product search autocomplete suggestions"""
    query = request.GET.get('q', '').strip()
    
    if not query or len(query) < 2:
        return JsonResponse({'suggestions': []})
    
    # Get approved products (allow both authenticated and anonymous users)
    if request.user.is_authenticated:
        if request.user.user_type == 'seller':
            products = Product.objects.filter(created_by=request.user)
        else:
            products = Product.objects.filter(status='approved')
    else:
        # Anonymous users can only see approved products
        products = Product.objects.filter(status='approved')
    
    # Search in name, brand, and description
    products = products.filter(
        models.Q(name__icontains=query) |
        models.Q(brand__icontains=query) |
        models.Q(description__icontains=query)
    )[:10]  # Limit to 10 suggestions
    
    suggestions = []
    for product in products:
        suggestions.append({
            'id': product.id,
            'name': product.name,
            'brand': product.brand,
            'price': str(product.price),
            'image': product.image.url if product.image else '',
        })
    
    return JsonResponse({'suggestions': suggestions})


def product_detail(request, product_id):
    from .models import UserHistory, Favorite
    product = get_object_or_404(Product.objects.prefetch_related('additional_images'), id=product_id)
    
    # Only show approved products to anonymous users
    if not request.user.is_authenticated and product.status != 'approved':
        messages.error(request, 'This product is not available.')
        return redirect('product_list')
    
    reviews = product.reviews.all().select_related('user').order_by('-created_at')
    
    # Track user history only for authenticated users
    is_favorited = False
    if request.user.is_authenticated:
        UserHistory.objects.get_or_create(
            user=request.user,
            product=product,
            defaults={'viewed_at': timezone.now()}
        )
        
        # Check if favorited (only for authenticated users)
        if request.user.user_type == 'user':
            is_favorited = Favorite.objects.filter(user=request.user, product=product).exists()
    
    # Process image index for slider
    current_index = request.GET.get('img', '0')
    try:
        product.current_image_index = int(current_index)
    except (ValueError, TypeError):
        product.current_image_index = 0
    
    return render(request, 'accounts/product_detail.html', {
        'product': product,
        'reviews': reviews,
        'is_favorited': is_favorited,
        'user': request.user
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
            messages.success(request, f'Removed "{product.name}" from favorites.')
        else:
            messages.success(request, f'Added "{product.name}" to favorites.')
        
        return redirect('product_detail', product_id=product_id)
    return redirect('product_detail', product_id=product_id)


@login_required
def favorites_list(request):
    from .models import Favorite
    favorites = Favorite.objects.filter(user=request.user).select_related('product').prefetch_related('product__additional_images')
    
    # Process image indices for each product
    for favorite in favorites:
        product = favorite.product
        img_param = f'img_{product.id}'
        current_index = request.GET.get(img_param, '0')
        try:
            product.current_image_index = int(current_index)
        except (ValueError, TypeError):
            product.current_image_index = 0
    
    return render(request, 'accounts/favorites.html', {'favorites': favorites})


@login_required
def user_history(request):
    from .models import UserHistory
    history = UserHistory.objects.filter(user=request.user).select_related('product')[:20]
    return render(request, 'accounts/history.html', {'history': history})


def buy_product(request, product_id):
    from django.contrib.auth import get_user_model
    from django.utils.text import slugify
    
    product = get_object_or_404(Product, id=product_id)
    User = get_user_model()
    
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        total_price = product.price * quantity
        payment_method = request.POST.get('payment_method')
        
        # Handle authenticated users vs guest checkout
        if request.user.is_authenticated:
            # Registered user - create order with user
            order = Order.objects.create(
                user=request.user,
                product=product,
                seller=product.created_by,
                quantity=quantity,
                total_price=total_price
            )
        else:
            # Guest checkout - collect guest information
            email = request.POST.get('email', '').strip()
            full_name = request.POST.get('full_name', '').strip()
            phone = request.POST.get('phone', '').strip()
            address = request.POST.get('address', '').strip()
            
            if not email or not full_name:
                from django.contrib import messages
                messages.error(request, 'Please provide your email and full name to complete the purchase.')
                return render(request, 'accounts/buy_product.html', {'product': product, 'is_guest': True})
            
            # Create order without user account
            order = Order.objects.create(
                user=None,  # No user account created
                product=product,
                seller=product.created_by,
                quantity=quantity,
                total_price=total_price,
                guest_name=full_name,
                guest_email=email,
                guest_phone=phone,
                guest_address=address
            )
        
        # Show order confirmation
        return render(request, 'accounts/order_confirmation.html', {
            'order_ids': [order.id],
            'payment_method': payment_method
        })
    
    # GET request - check if user is authenticated
    is_guest = not request.user.is_authenticated
    return render(request, 'accounts/buy_product.html', {
        'product': product,
        'is_guest': is_guest
    })


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
            
            # Generate token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Create reset link
            reset_link = request.build_absolute_uri(
                f'/password-reset-confirm/{uid}/{token}/'
            )
            
            # Send email
            subject = 'EcoRate - Password Reset Request'
            message = f'''Hi {user.username},

You requested a password reset for your EcoRate account.

Click the link below to reset your password:
{reset_link}

This link will expire in 24 hours for security reasons.

If you didn't request this, please ignore this email.

Best regards,
EcoRate Team'''
            
            # Send email to console for development
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            messages.success(request, 'Password reset instructions have been sent. Check the console for the reset link.')
            
            return redirect('login')
        except CustomUser.DoesNotExist:
            messages.error(request, 'No account found with this email address.')
    
    return render(request, 'accounts/password_reset.html')

@login_required
def add_product(request):
    if request.user.user_type != 'seller':
        messages.error(request, 'Access denied. Seller account required.')
        return redirect('login')
    
    if request.method == 'POST':
        # Check if custom category is being created
        custom_category_name = request.POST.get('custom_category_name')
        
        if custom_category_name:
            # Create new category
            custom_category_desc = request.POST.get('custom_category_desc', '')
            category, created = Category.objects.get_or_create(
                name=custom_category_name,
                defaults={'description': custom_category_desc}
            )
            
            # Modify POST data to use the new category
            post_data = request.POST.copy()
            post_data['category'] = category.id
            form = ProductForm(post_data, request.FILES)
        else:
            form = ProductForm(request.POST, request.FILES)
        
        if form.is_valid():
            product = form.save(commit=False)
            product.created_by = request.user
            product.save()
            
            # Handle multiple additional images
            additional_images = request.FILES.getlist('additional_images')
            for image in additional_images:
                ProductImage.objects.create(product=product, image=image)
            
            if custom_category_name:
                messages.success(request, f'New category "{custom_category_name}" created and product "{product.name}" added successfully!')
            else:
                messages.success(request, f'Product "{product.name}" has been added successfully!')
            return redirect('seller_home')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProductForm()
    
    return render(request, 'accounts/add_product.html', {'form': form})

@login_required
def seller_products(request):
    if request.user.user_type != 'seller':
        messages.error(request, 'Access denied. Seller account required.')
        return redirect('login')
    
    products = Product.objects.filter(created_by=request.user).select_related('category').prefetch_related('additional_images')
    categories = Category.objects.all()
    
    # Process image indices for each product
    for product in products:
        img_param = f'img_{product.id}'
        current_index = request.GET.get(img_param, '0')
        try:
            product.current_image_index = int(current_index)
        except (ValueError, TypeError):
            product.current_image_index = 0
    
    return render(request, 'accounts/seller_products.html', {
        'products': products,
        'categories': categories
    })

def admin_login_view(request):
    if request.user.is_authenticated and request.user.user_type == 'admin':
        return redirect('admin_home')

    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.user_type == 'admin':
                login(request, user)
                messages.success(request, f'Welcome, Administrator {user.username}!')
                return redirect('admin_home')
            else:
                messages.error(request, 'Access denied. Administrator credentials required.')
        else:
            messages.error(request, 'Invalid administrator credentials.')
    else:
        form = CustomLoginForm()
    return render(request, 'accounts/admin_login.html', {'form': form})

@login_required
def admin_products(request):
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied. Admin account required.')
        return redirect('login')
    
    products = Product.objects.all().select_related('created_by', 'category').prefetch_related('additional_images').order_by('-created_at')
    
    # Process image indices for each product
    for product in products:
        img_param = f'img_{product.id}'
        current_index = request.GET.get(img_param, '0')
        try:
            product.current_image_index = int(current_index)
        except (ValueError, TypeError):
            product.current_image_index = 0
    
    return render(request, 'accounts/admin_products.html', {'products': products})

@login_required
def admin_users(request):
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied. Admin account required.')
        return redirect('login')
    
    users = CustomUser.objects.all().order_by('-date_joined')
    return render(request, 'accounts/admin_users.html', {'users': users})

@login_required
def admin_reviews(request):
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied. Admin account required.')
        return redirect('login')
    
    reviews = Review.objects.all().select_related('user', 'product').order_by('-created_at')
    return render(request, 'accounts/admin_reviews.html', {'reviews': reviews})

@login_required
def admin_categories(request):
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied. Admin account required.')
        return redirect('login')
    
    categories = Category.objects.all()
    return render(request, 'accounts/admin_categories.html', {'categories': categories})

@login_required
def admin_orders(request):
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied. Admin account required.')
        return redirect('login')
    
    from .models import Order
    orders = Order.objects.all().select_related('user', 'product', 'seller').order_by('-order_date')
    
    # Order statistics
    total_orders = orders.count()
    pending_orders = orders.filter(status='pending').count()
    confirmed_orders = orders.filter(status='confirmed').count()
    shipped_orders = orders.filter(status='shipped').count()
    completed_orders = orders.filter(status='completed').count()
    cancelled_orders = orders.filter(status='cancelled').count()
    guest_orders = orders.filter(user__isnull=True).count()
    
    return render(request, 'accounts/admin_orders.html', {
        'orders': orders,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'confirmed_orders': confirmed_orders,
        'shipped_orders': shipped_orders,
        'completed_orders': completed_orders,
        'cancelled_orders': cancelled_orders,
        'guest_orders': guest_orders
    })

@login_required
def admin_approvals(request):
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied. Admin account required.')
        return redirect('login')
    
    pending_products = Product.objects.filter(status='pending').select_related('created_by', 'category').prefetch_related('additional_images').order_by('-created_at')
    
    # Process image indices for each product
    for product in pending_products:
        img_param = f'img_{product.id}'
        current_index = request.GET.get(img_param, '0')
        try:
            product.current_image_index = int(current_index)
        except (ValueError, TypeError):
            product.current_image_index = 0
    
    return render(request, 'accounts/admin_approvals.html', {'pending_products': pending_products})

@login_required
def approve_product(request, product_id):
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied. Admin account required.')
        return redirect('admin_home')
    
    if request.method == 'POST':
        try:
            product = Product.objects.get(id=product_id)
            action = request.POST.get('action')
            
            if action == 'approve':
                product.status = 'approved'
                product.approved_at = timezone.now()
                product.save()
                messages.success(request, f'Product "{product.name}" has been approved!')
            elif action == 'reject':
                product.status = 'rejected'
                product.save()
                messages.success(request, f'Product "{product.name}" has been rejected!')
            else:
                messages.error(request, 'Invalid action.')
        except Product.DoesNotExist:
            messages.error(request, 'Product not found.')
    
    return redirect('admin_approvals')


def password_reset_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            password1 = request.POST.get('password1')
            password2 = request.POST.get('password2')
            
            if password1 and password2:
                if password1 == password2:
                    if len(password1) >= 8:
                        user.set_password(password1)
                        user.save()
                        messages.success(request, 'Your password has been reset successfully! You can now log in.')
                        return redirect('login')
                    else:
                        messages.error(request, 'Password must be at least 8 characters long.')
                else:
                    messages.error(request, 'Passwords do not match.')
            else:
                messages.error(request, 'Please fill in both password fields.')
        
        return render(request, 'accounts/password_reset_confirm.html', {
            'validlink': True,
            'uidb64': uidb64,
            'token': token
        })
    else:
        messages.error(request, 'The password reset link is invalid or has expired.')
        return redirect('password_reset')