from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary using the key"""
    return dictionary.get(key)

@register.filter
def signature_status_class(message):
    """Return CSS class based on message signature status"""
    if not message.get('is_signed', False):
        return ""
    return "success" if message.get('signature_verified', False) else "danger"