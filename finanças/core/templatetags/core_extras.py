from django import template

register = template.Library()

@register.filter(name='multiply')
@register.filter(name='mul')
def multiply(value, arg):
    """Multiply two template values; registered under both 'multiply' and 'mul' since both are used across templates."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def brl(value):
    """Format as Brazilian Real: R$ 1.234,56"""
    try:
        f = float(value)
        negative = f < 0
        formatted = f"{abs(f):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        prefix = "- R$ " if negative else "R$ "
        return prefix + formatted
    except (ValueError, TypeError):
        return "R$ 0,00"
