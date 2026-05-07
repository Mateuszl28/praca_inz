import time
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def antybot_pola():
    """Honeypot + timestamp do walidacji po stronie serwera (_antybot w views)."""
    return mark_safe(
        '<input type="text" name="_pulapka" tabindex="-1" autocomplete="off" '
        'style="position:absolute;left:-9999px;width:1px;height:1px;opacity:0;" aria-hidden="true">'
        f'<input type="hidden" name="_ts" value="{int(time.time())}">'
    )
