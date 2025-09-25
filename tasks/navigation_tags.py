from django import template
from tasks.models import NavigationButton

register = template.Library()

@register.simple_tag
def get_navigation_buttons():
    return NavigationButton.objects.filter(is_active=True)