from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from .models import Item, Category, Cart, CartItem, Order, OrderItem, Payment
from .forms import ItemForm, ItemSearchForm, CheckoutForm, PaymentForm
from users.models import UserBlock

@login_required
def marketplace_home(request):
    # Only verified users can access the marketplace
    if not request.user.is_verified:
        messages.warning(request, "You need to verify your account to access the marketplace.")
        return redirect('verification_request')
    
    form = ItemSearchForm(request.GET)

    # Get users who have blocked me or who I've blocked
    blocked_by_me = UserBlock.objects.filter(blocker=request.user).values_list('blocked_user', flat=True)
    blocking_me = UserBlock.objects.filter(blocked_user=request.user).values_list('blocker', flat=True)
    blocked_users = list(blocked_by_me) + list(blocking_me)
    
    # Base queryset of available items, excluding blocked users' items
    items = Item.objects.filter(status='available').exclude(seller__in=blocked_users)
    
    # Base queryset of available items
    items = Item.objects.filter(status='available')
    
    # Apply filters if form is valid
    if form.is_valid():
        search_query = form.cleaned_data.get('search_query')
        category = form.cleaned_data.get('category')
        min_price = form.cleaned_data.get('min_price')
        max_price = form.cleaned_data.get('max_price')
        
        if search_query:
            items = items.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        if category:
            items = items.filter(category_id=category)
        
        if min_price is not None:
            items = items.filter(price__gte=min_price)
        
        if max_price is not None:
            items = items.filter(price__lte=max_price)
    
    # Get categories for the sidebar
    categories = Category.objects.all()
    
    return render(request, 'marketplace/home.html', {
        'items': items,
        'categories': categories,
        'form': form
    })

@login_required
def item_detail(request, item_id):
    # Only verified users can access item details
    if not request.user.is_verified:
        messages.warning(request, "You need to verify your account to access the marketplace.")
        return redirect('verification_request')
    
    item = get_object_or_404(Item, id=item_id)

    # Check for blocks
    if UserBlock.objects.filter(
        (Q(blocker=request.user) & Q(blocked_user=item.seller)) |
        (Q(blocker=item.seller) & Q(blocked_user=request.user))
    ).exists():
        messages.error(request, "You cannot view this item due to a user block.")
        return redirect('marketplace_home')
    return render(request, 'marketplace/item_detail.html', {'item': item})

@login_required
def add_item(request):
    # Only verified users can add items
    if not request.user.is_verified:
        messages.warning(request, "You need to verify your account to sell items.")
        return redirect('verification_request')
    
    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.seller = request.user
            item.save()
            messages.success(request, f"'{item.name}' has been added to the marketplace.")
            return redirect('item_detail', item_id=item.id)
    else:
        form = ItemForm()
    
    return render(request, 'marketplace/add_item.html', {'form': form})

@login_required
def edit_item(request, item_id):
    # Only verified users can edit items
    if not request.user.is_verified:
        messages.warning(request, "You need to verify your account to edit items.")
        return redirect('verification_request')
    
    item = get_object_or_404(Item, id=item_id, seller=request.user)
    
    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, f"'{item.name}' has been updated.")
            return redirect('item_detail', item_id=item.id)
    else:
        form = ItemForm(instance=item)
    
    return render(request, 'marketplace/edit_item.html', {'form': form, 'item': item})

@login_required
def delete_item(request, item_id):
    # Only verified users can delete items
    if not request.user.is_verified:
        messages.warning(request, "You need to verify your account to delete items.")
        return redirect('verification_request')
    
    item = get_object_or_404(Item, id=item_id, seller=request.user)
    
    if request.method == 'POST':
        item_name = item.name
        item.delete()
        messages.success(request, f"'{item_name}' has been deleted.")
        return redirect('my_items')
    
    return render(request, 'marketplace/delete_item.html', {'item': item})

@login_required
def my_items(request):
    # Only verified users can see their items
    if not request.user.is_verified:
        messages.warning(request, "You need to verify your account to sell items.")
        return redirect('verification_request')
    
    items = Item.objects.filter(seller=request.user).order_by('-created_at')
    return render(request, 'marketplace/my_items.html', {'items': items})

@login_required
def add_to_cart(request, item_id):
    # Only verified users can add items to cart
    if not request.user.is_verified:
        messages.warning(request, "You need to verify your account to make purchases.")
        return redirect('verification_request')
    
    item = get_object_or_404(Item, id=item_id, status='available')

    # Check for blocks
    if UserBlock.objects.filter(
        (Q(blocker=request.user) & Q(blocked_user=item.seller)) |
        (Q(blocker=item.seller) & Q(blocked_user=request.user))
    ).exists():
        messages.error(request, "You cannot purchase items from this seller.")
        return redirect('marketplace_home')
    
    # Don't allow adding your own items to cart
    if item.seller == request.user:
        messages.warning(request, "You cannot purchase your own items.")
        return redirect('item_detail', item_id=item.id)
    
    # Get or create user's cart
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    # Check if item already in cart
    cart_item, created = CartItem.objects.get_or_create(cart=cart, item=item)
    
    if not created:
        # Item already in cart, increment quantity
        cart_item.quantity += 1
        cart_item.save()
        messages.info(request, f"Increased quantity of '{item.name}' in your cart.")
    else:
        messages.success(request, f"Added '{item.name}' to your cart.")
    
    return redirect('view_cart')

@login_required
def remove_from_cart(request, item_id):
    # Only verified users can remove items from cart
    if not request.user.is_verified:
        messages.warning(request, "You need to verify your account to make purchases.")
        return redirect('verification_request')
    
    # Get cart
    cart = get_object_or_404(Cart, user=request.user)
    
    # Get cart item
    cart_item = get_object_or_404(CartItem, cart=cart, item_id=item_id)
    
    # Remove item from cart
    cart_item.delete()
    messages.success(request, "Item removed from cart.")
    
    return redirect('view_cart')

@login_required
def update_cart_quantity(request, item_id):
    # Only verified users can update cart
    if not request.user.is_verified:
        messages.warning(request, "You need to verify your account to make purchases.")
        return redirect('verification_request')
    
    # Get cart
    cart = get_object_or_404(Cart, user=request.user)
    
    # Get cart item
    cart_item = get_object_or_404(CartItem, cart=cart, item_id=item_id)
    
    # Update quantity
    quantity = int(request.POST.get('quantity', 1))
    if quantity < 1:
        cart_item.delete()
        messages.success(request, "Item removed from cart.")
    else:
        cart_item.quantity = quantity
        cart_item.save()
        messages.success(request, "Cart updated.")
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'total_price': cart.total_price,
            'total_items': cart.total_items,
        })
    
    return redirect('view_cart')

@login_required
def view_cart(request):
    # Only verified users can view cart
    if not request.user.is_verified:
        messages.warning(request, "You need to verify your account to make purchases.")
        return redirect('verification_request')
    
    # Get or create user's cart
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    # Get cart items
    cart_items = cart.items.all().select_related('item')
    
    return render(request, 'marketplace/cart.html', {
        'cart': cart,
        'cart_items': cart_items
    })

@login_required
def checkout(request):
    # Only verified users can checkout
    if not request.user.is_verified:
        messages.warning(request, "You need to verify your account to make purchases.")
        return redirect('verification_request')
    
    # Get cart
    cart = get_object_or_404(Cart, user=request.user)
    
    # Check if cart is empty
    if cart.items.count() == 0:
        messages.warning(request, "Your cart is empty.")
        return redirect('marketplace_home')
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Create order
            order = form.save(commit=False)
            order.user = request.user
            order.total_price = cart.total_price
            order.status = 'pending'
            order.save()
            
            # Create order items
            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    item_name=cart_item.item.name,
                    item_price=cart_item.item.price,
                    quantity=cart_item.quantity,
                    original_item=cart_item.item,
                    seller=cart_item.item.seller
                )
                
                # Mark items as reserved
                item = cart_item.item
                item.status = 'reserved'
                item.save()
            
            # Clear cart
            cart.items.all().delete()
            
            messages.success(request, "Your order has been created! Proceed to payment.")
            return redirect('payment', order_id=order.id)
    else:
        form = CheckoutForm()
    
    return render(request, 'marketplace/checkout.html', {
        'form': form,
        'cart': cart,
        'cart_items': cart.items.all()
    })

@login_required
def payment(request, order_id):
    # Only verified users can make payments
    if not request.user.is_verified:
        messages.warning(request, "You need to verify your account to make payments.")
        return redirect('verification_request')
    
    # Get order
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Check if order is already paid
    if order.status == 'paid':
        messages.info(request, "This order has already been paid for.")
        return redirect('order_confirmation', order_id=order.id)
    
    # Update order status to payment_initiated
    if order.status in ['pending', 'cancelled']:
        order.status = 'payment_initiated'
        order.save()
        
        # Update item status to reserved if they were available
        for order_item in order.items.all():
            if order_item.original_item and order_item.original_item.status == 'available':
                order_item.original_item.status = 'reserved'
                order_item.original_item.save()
    
    if request.method == 'POST':
        # Process the payment form as before
        form = PaymentForm(request.POST)
        if form.is_valid():
            # Create payment or update existing
            try:
                payment = Payment.objects.get(order=order)
                # Update payment details
                payment.payment_method = form.cleaned_data.get('payment_method')
            except Payment.DoesNotExist:
                payment = form.save(commit=False)
                payment.order = order
                payment.amount = order.total_price
            
            # Get card details
            card_number = form.cleaned_data.get('card_number')
            card_expiry_month = form.cleaned_data.get('card_expiry_month')
            card_expiry_year = form.cleaned_data.get('card_expiry_year')
            
            # Store last 4 digits and expiry (for demonstration only)
            payment.card_number_last4 = card_number[-4:]
            payment.card_expiry = f"{card_expiry_month}/{card_expiry_year}"
            
            # Simulate payment processing
            import random
            import time
            import string
            
            # Generate a random transaction ID
            transaction_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
            payment.transaction_id = transaction_id
            
            # Simulate processing delay
            time.sleep(1)
            
            # 95% success rate for demo purposes
            if random.random() < 0.95:
                payment.status = 'completed'
                order.status = 'paid'
                
                # Mark items as sold
                for order_item in order.items.all():
                    if order_item.original_item:
                        order_item.original_item.status = 'sold'
                        order_item.original_item.save()
                
                messages.success(request, "Payment successful! Your order has been confirmed.")
            else:
                payment.status = 'failed'
                order.status = 'pending'
                
                # Mark items as available again
                for order_item in order.items.all():
                    if order_item.original_item:
                        order_item.original_item.status = 'available'
                        order_item.original_item.save()
                
                messages.error(request, "Payment failed. Please try again or use a different payment method.")
            
            payment.save()
            order.payment_id = str(payment.id)
            order.save()
            
            if payment.status == 'completed':
                messages.success(request, "Your order has been placed successfully. You can track its status in My Orders.")
                return redirect('payment_success', order_id=order.id)
            else:
                return redirect('payment', order_id=order.id)
    else:
        # Check if a payment already exists for this order
        try:
            existing_payment = Payment.objects.get(order=order)
            form = PaymentForm(instance=existing_payment)
        except Payment.DoesNotExist:
            form = PaymentForm()
    
    return render(request, 'marketplace/payment.html', {
        'form': form,
        'order': order
    })

@login_required
def payment_success(request, order_id):
    # Only verified users can see payment confirmation
    if not request.user.is_verified:
        messages.warning(request, "You need to verify your account to access this page.")
        return redirect('verification_request')
    
    # Get order
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Make sure order is paid
    if order.status != 'paid':
        messages.warning(request, "This order has not been paid for yet.")
        return redirect('payment', order_id=order.id)
    
    try:
        payment = Payment.objects.get(order=order)
    except Payment.DoesNotExist:
        payment = None
    
    return render(request, 'marketplace/payment_success.html', {
        'order': order,
        'payment': payment
    })

@login_required
def order_confirmation(request, order_id):
    # Only verified users can see order confirmations
    if not request.user.is_verified:
        messages.warning(request, "You need to verify your account to make purchases.")
        return redirect('verification_request')
    
    # Get order
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    try:
        # Get payment details if exists
        payment = Payment.objects.get(order=order)
    except Payment.DoesNotExist:
        payment = None
    
    return render(request, 'marketplace/order_confirmation.html', {
        'order': order,
        'payment': payment
    })

@login_required
def my_orders(request):
    # Only verified users can see their orders
    if not request.user.is_verified:
        messages.warning(request, "You need to verify your account to make purchases.")
        return redirect('verification_request')
    
    # Get orders
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    return render(request, 'marketplace/my_orders.html', {'orders': orders})

@login_required
def sold_items(request):
    # Only verified users can see their sold items
    if not request.user.is_verified:
        messages.warning(request, "You need to verify your account to sell items.")
        return redirect('verification_request')
    
    # Get sold items
    sold_items = OrderItem.objects.filter(seller=request.user).order_by('-order__created_at')
    
    # Calculate total revenue
    total_revenue = 0
    for item in sold_items:
        total_revenue += item.item_price * item.quantity
    
    # Get unique buyers
    unique_buyers = set()
    for item in sold_items:
        unique_buyers.add(item.order.user.username)
    
    return render(request, 'marketplace/sold_items.html', {
        'sold_items': sold_items,
        'total_revenue': total_revenue,
        'unique_buyers_count': len(unique_buyers)
    })

@login_required
def delete_order(request, order_id):
    # Only verified users can delete orders
    if not request.user.is_verified:
        messages.warning(request, "You need to verify your account to manage orders.")
        return redirect('verification_request')
    
    # Get order
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Only pending orders can be deleted
    if order.status != 'pending':
        messages.error(request, "Only pending orders can be deleted.")
        return redirect('my_orders')
    
    if request.method == 'POST':
        # Return reserved items to available status
        for order_item in order.items.all():
            if order_item.original_item:
                order_item.original_item.status = 'available'
                order_item.original_item.save()
        
        # Delete the order
        order.delete()
        messages.success(request, "Order has been deleted successfully.")
        return redirect('my_orders')
    
    return render(request, 'marketplace/delete_order.html', {'order': order})