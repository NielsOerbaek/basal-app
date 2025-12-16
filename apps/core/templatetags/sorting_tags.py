from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from urllib.parse import urlencode

register = template.Library()


@register.simple_tag(takes_context=True)
def sort_header(context, field, label):
    """
    Render a sortable table header.

    Usage: {% sort_header 'name' 'Navn' %}
    """
    request = context['request']
    current_sort = context.get('current_sort')
    current_order = context.get('current_order', 'asc')

    # Build new query params
    params = request.GET.copy()

    # Determine new order
    if current_sort == field:
        new_order = 'desc' if current_order == 'asc' else 'asc'
    else:
        new_order = 'asc'

    params['sort'] = field
    params['order'] = new_order

    url = f'?{urlencode(params)}'

    # Build icon
    if current_sort == field:
        if current_order == 'asc':
            icon = mark_safe('<i class="bi bi-sort-up ms-1"></i>')
        else:
            icon = mark_safe('<i class="bi bi-sort-down ms-1"></i>')
    else:
        icon = ''

    return format_html(
        '<a href="{}" class="text-decoration-none text-dark">{}</a>{}',
        url,
        label,
        icon
    )
