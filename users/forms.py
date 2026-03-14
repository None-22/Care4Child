from django import forms
from django.contrib.auth.forms import AuthenticationForm
from centers.models import HealthCenter

class CenterLoginForm(AuthenticationForm):
    username = forms.CharField(label="اسم المستخدم", widget=forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'أدخل اسم المستخدم'}))
    password = forms.CharField(label="كلمة المرور", widget=forms.PasswordInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'أدخل كلمة المرور'}))
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UsernameField
from centers.models import HealthCenter

class CenterLoginForm(AuthenticationForm):
    # نستخدم UsernameField بدلاً من CharField العادي لأنه يطبّق تحويل NFKC Unicode
    # وهذا ضروري لدعم اليوزرنيم العربي — بدونه يختلف شكل الحروف المحفوظة عن المكتوبة
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