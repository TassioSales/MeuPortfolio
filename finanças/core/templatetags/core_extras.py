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


@register.filter
def absval(value):
    try:
        return abs(value)
    except TypeError:
        return value


@register.filter
def pct(value, decimals=0):
    """12.345 → '12%' (ou '12,3%' com decimals=1)."""
    try:
        return f"{float(value):.{int(decimals)}f}".replace('.', ',') + '%'
    except (ValueError, TypeError):
        return '—'


@register.simple_tag
def delta_badge(change, higher_is_good=True, suffix='vs. período anterior'):
    """Badge de variação %: verde quando a mudança é boa (receita subindo,
    despesa caindo), vermelho quando é ruim."""
    from django.utils.html import format_html
    if change is None:
        return ''
    value = float(change)
    if abs(value) < 0.5:
        css = 'delta-neutral'
    else:
        good = (value > 0) == bool(higher_is_good)
        css = 'delta-good' if good else 'delta-bad'
    arrow = '▲' if value > 0 else ('▼' if value < 0 else '•')
    text = f"{abs(value):.0f}%"
    return format_html('<span class="delta {}" title="{}">{} {}</span>', css, suffix, arrow, text)


@register.filter
def in_list(value, container):
    try:
        return value in container
    except TypeError:
        return False
