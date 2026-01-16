from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key."""
    if dictionary is None:
        return None
    return dictionary.get(key)

@register.filter
def multiply(value, arg):
    """Multiply the value by the argument."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''
    
@register.filter
def map(value, arg):
    """Get an attribute from each item in a list."""
    if not value:
        return []
    
    result = []
    for item in value:
        # Handle nested attributes like 'order.user.id'
        attrs = arg.split('.')
        current = item
        try:
            for attr in attrs:
                current = getattr(current, attr)
            result.append(current)
        except (AttributeError, TypeError):
            continue
    return result

@register.filter
def unique(value):
    """Return only unique items from a list."""
    return list(set(value))

@register.filter
def sum(value):
    """Sum values in a list."""
    return sum(value)

@register.filter
def split(value, arg):
    """Split the value by the argument."""
    return value.split(arg)