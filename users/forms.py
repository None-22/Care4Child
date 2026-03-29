from django import forms
from django.contrib.auth.forms import AuthenticationForm, UsernameField
from centers.models import HealthCenter

class CenterLoginForm(AuthenticationForm):
    username = UsernameField(
        label="اسم المستخدم",
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'أدخل اسم المستخدم',
            'autocomplete': 'username',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        label="كلمة المرور",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'أدخل كلمة المرور',
            'autocomplete': 'current-password',
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        user = self.get_user()
        
        if user is not None:
            # نتحقق من الدور (Role) أولاً
            if user.role in ['CENTER_MANAGER', 'CENTER_STAFF']:
                # التحقق من حالة المركز (للموظفين والمدراء)
                if hasattr(user, 'health_center') and user.health_center:
                    if not user.health_center.is_active:
                        if user.role == 'CENTER_STAFF':
                            error_msg = "عذراً، المركز الصحي التابع لك موقوف حالياً، ولذلك تم إيقاف صلاحية دخولك للنظام كموظف."
                        else:
                            error_msg = "عذراً، هذا المركز الصحي موقوف حالياً. لا يمكنك تسجيل الدخول."
                            
                        raise forms.ValidationError(error_msg, code='inactive_center')
        return cleaned_data