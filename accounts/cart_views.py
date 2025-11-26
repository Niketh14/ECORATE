from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Cart, Order, Product

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart_item, created = Cart.objects.get_or_create(
        user=request.user,
        product=product,
        defaults={'quantity': 1}
    )
    
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    
    messages.success(request, f'{product.name} added to cart!')
    return redirect('product_detail', product_id=product.id)

@login_required
def cart_view(request):
    cart_items = Cart.objects.filter(user=request.user).select_related('product')
    total = sum(item.total_price for item in cart_items)
    return render(request, 'accounts/cart.html', {
        'cart_items': cart_items,
        'total': total
    })

@login_required
def remove_from_cart(request, cart_id):
    cart_item = get_object_or_404(Cart, id=cart_id, user=request.user)
    product_name = cart_item.product.name
    cart_item.delete()
    messages.success(request, f'{product_name} removed from cart!')
    return redirect('cart')

@login_required
def checkout(request):
    cart_items = Cart.objects.filter(user=request.user).select_related('product')
    
    if not cart_items:
        messages.error(request, 'Your cart is empty!')
        return redirect('cart')
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        
        # Create orders for each cart item
        order_ids = []
        for item in cart_items:
            order = Order.objects.create(
                user=request.user,
                product=item.product,
                seller=item.product.created_by,
                quantity=item.quantity,
                total_price=item.total_price
            )
            order_ids.append(order.id)
        
        # Clear cart
        cart_items.delete()
        
        # Show order confirmation
        return render(request, 'accounts/order_confirmation.html', {
            'order_ids': order_ids,
            'payment_method': payment_method
        })
    
    total = sum(item.total_price for item in cart_items)
    return render(request, 'accounts/checkout.html', {
        'cart_items': cart_items,
        'total': total
    })

@login_required
def user_orders(request):
    orders = Order.objects.filter(user=request.user).select_related('product').order_by('-order_date')
    return render(request, 'accounts/user_orders.html', {'orders': orders})

@login_required
def seller_orders(request):
    if request.user.user_type != 'seller':
        messages.error(request, 'Access denied. Seller account required.')
        return redirect('login')
    
    orders = Order.objects.filter(seller=request.user).select_related('product', 'user').order_by('-order_date')
    
    # Order counts for dashboard
    pending_count = orders.filter(status='pending').count()
    confirmed_count = orders.filter(status='confirmed').count()
    shipped_count = orders.filter(status='shipped').count()
    
    return render(request, 'accounts/seller_orders.html', {
        'orders': orders,
        'pending_count': pending_count,
        'confirmed_count': confirmed_count,
        'shipped_count': shipped_count
    })

@login_required
def update_order_status(request, order_id):
    if request.user.user_type != 'seller':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    order = get_object_or_404(Order, id=order_id, seller=request.user)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['pending', 'confirmed', 'shipped', 'completed', 'cancelled']:
            order.status = new_status
            
            if new_status == 'confirmed':
                order.stock_confirmed = True
                order.confirmed_date = timezone.now()
                messages.success(request, f'Order #{order.id} stock confirmed!')
            elif new_status == 'shipped':
                order.shipped_date = timezone.now()
                messages.success(request, f'Order #{order.id} marked as shipped!')
            elif new_status == 'completed':
                order.completed_date = timezone.now()
                messages.success(request, f'Order #{order.id} completed!')
            elif new_status == 'cancelled':
                messages.info(request, f'Order #{order.id} cancelled.')
            
            order.save()
    
    return redirect('seller_orders')