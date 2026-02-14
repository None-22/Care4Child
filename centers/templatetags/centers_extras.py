from django import template
import math

register = template.Library()

@register.filter
def format_age_ar(val):
    try:
        val = float(val)
    except (ValueError, TypeError):
        return val

    if val == 0:
        return "عند الولادة"
    
    # Handle halves
    whole = int(val)
    fraction = val - whole
    
    is_half = abs(fraction - 0.5) < 0.01
    
    if is_half:
        if whole == 0:
            return "نصف شهر"
        elif whole == 1:
            return "شهر ونصف"
        elif whole == 2:
            return "شهرين ونصف"
        elif whole >= 3 and whole <= 10:
            return f"{whole} أشهر ونصف"
        else:
            return f"{whole} شهر ونصف"
    else:
        # Integers
        if whole == 1:
            return "شهر"
        elif whole == 2:
            return "شهرين"
        elif whole >= 3 and whole <= 10:
            return f"{whole} أشهر"
        else:
            return f"{whole} شهر"
