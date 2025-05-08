from django import template

register = template.Library()

@register.filter
def div(value, arg):
    """Divide o valor pelo argumento"""
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def mul(value, arg):
    """Multiplica o valor pelo argumento"""
    try:
        return float(value) * float(arg)
    except (ValueError, ZeroDivisionError):
        return 0 