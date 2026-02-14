from django import forms
from django.contrib.auth.forms import AuthenticationForm
from centers.models import HealthCenter

class CenterLoginForm(AuthenticationForm):
    username = forms.CharField(label="اسم المستخدم", widget=forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'أدخل اسم المستخدم'}))
    password = forms.CharField(label="كلمة المرور", widget=forms.PasswordInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'أدخل كلمة المرور'}))
