from django import template

register = template.Library()

@register.filter
def get_item(queryset, index):
    """Get item at specific index from queryset"""
    try:
        return list(queryset)[int(index)]
    except (IndexError, ValueError, TypeError):
        return None

@register.filter
def subtract(value, arg):
    """Subtract arg from value"""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def add_one(value):
    """Add 1 to value"""
    try:
        return int(value) + 1
    except (ValueError, TypeError):
        return 1