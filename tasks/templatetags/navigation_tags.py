from django import template
from tasks.models import NavigationButton

register = template.Library()

@register.simple_tag
def get_navigation_buttons(user):
    if user.is_authenticated and user.is_staff:
        return NavigationButton.objects.filter(is_active=True).order_by('order')
    return NavigationButton.objects.none()