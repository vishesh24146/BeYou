from friends.models import Notification
from marketplace.models import Cart

def notification_count(request):
    """Add notification count to the context."""
    count = 0
    if request.user.is_authenticated:
        count = Notification.objects.filter(user=request.user, is_read=False).count()
    return {'notification_count': count}

def cart_count(request):
    """Add cart item count to the context."""
    count = 0
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            count = cart.total_items
        except Cart.DoesNotExist:
            pass
    return {'cart_item_count': count}