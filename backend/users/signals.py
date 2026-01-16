from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from .models import LoginActivity
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser, UserKey
from messaging.utils import generate_key_pair
import logging
from django.contrib.auth.signals import user_logged_in

@receiver(user_logged_in)
def retrieve_keys_on_login(sender, request, user, **kwargs):
    """Try to retrieve private keys from cache and store in session"""
    from django.core.cache import cache
    
    # Check if the cache has the user's private keys
    cache_key = f"user_private_keys_{user.id}"
    cached_keys = cache.get(cache_key)
    
    if cached_keys:
        # Store in session
        request.session['signing_private_key'] = cached_keys['signing_private_key']
        request.session['encryption_private_key'] = cached_keys['encryption_private_key']
        
        # Delete from cache after transferring to session
        cache.delete(cache_key)
        
        logger.info(f"Transferred private keys to session for user {user.username}")

logger = logging.getLogger(__name__)

@receiver(post_save, sender=CustomUser)
def generate_user_keys(sender, instance, created, **kwargs):
    """Generate cryptographic keys for new users"""
    if created:  # Only for newly created users
        try:
            # Generate signing key pair
            signing_keys = generate_key_pair()
            UserKey.objects.create(
                user=instance,
                public_key=signing_keys['public_key'],
                key_type='signing',
                is_active=True
            )
            
            # Generate encryption key pair
            encryption_keys = generate_key_pair()
            UserKey.objects.create(
                user=instance,
                public_key=encryption_keys['public_key'],
                key_type='encryption',
                is_active=True
            )
            
            # Store keys in user session's cache
            # We'll use a cache with the user's ID as a key
            from django.core.cache import cache
            cache_key = f"user_private_keys_{instance.id}"
            cache_data = {
                'signing_private_key': signing_keys['private_key'],
                'encryption_private_key': encryption_keys['private_key']
            }
            # Store for 1 hour (3600 seconds)
            cache.set(cache_key, cache_data, 3600)
            
            logger.info(f"Generated cryptographic keys for user {instance.username}")
        except Exception as e:
            logger.error(f"Error generating keys for user {instance.username}: {e}")

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    # Mark request to avoid duplicate logging
    request._login_attempt_logged = True

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    # Create logout entry
    if user and request:
        LoginActivity.objects.create(
            user=user,
            username=user.username,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            was_successful=True,
            failure_reason="User logged out"
        )

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip