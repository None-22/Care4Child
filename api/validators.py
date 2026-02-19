import re
from django.core.exceptions import ValidationError
from datetime import date

def validate_phone_number(value):
    """
    التحقق من صحة رقم الهاتف اليمني.
    - يجب أن يتكون من 9 أرقام.
    - يجب أن يبدأ بـ 70, 71, 73, 77, 78 أو 01.
    """
    if not value.isdigit():
        raise ValidationError("رقم الهاتف يجب أن يحتوي على أرقام فقط.")
    
    if len(value) != 9:
        raise ValidationError("رقم الهاتف يجب أن يتكون من 9 أرقام.")
    
    valid_prefixes = ['70', '71', '73', '77', '78', '01']
    if not any(value.startswith(prefix) for prefix in valid_prefixes):
        raise ValidationError(f"رقم الهاتف يجب أن يبدأ بـ {', '.join(valid_prefixes)}.")

def validate_name(value):
    """
    التحقق من صحة الأسماء.
    - يجب أن لا يحتوي على أرقام أو رموز خاصة.
    - السموج بحروف عربية أو إنجليزية.
    """
    # Regex for Arabic and English letters and spaces
    if not re.match(r'^[\u0600-\u06FFa-zA-Z\s]+$', value):
        raise ValidationError("الاسم يجب أن يحتوي على حروف فقط (عربية أو إنجليزية).")
    
    if len(value.strip()) < 2:
        raise ValidationError("الاسم قصير جداً.")

def validate_past_date(value):
    """
    التحقق من أن التاريخ ليس في المستقبل.
    """
    if value > date.today():
        raise ValidationError("التاريخ لا يمكن أن يكون في المستقبل.")
