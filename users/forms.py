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