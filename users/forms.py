from django import forms
from django.contrib.auth.forms import AuthenticationForm, UsernameField
from django.contrib.auth.password_validation import validate_password
from centers.models import HealthCenter
from django.contrib.auth import get_user_model

User = get_user_model()


class ProfileUpdateForm(forms.ModelForm):
    new_password1 = forms.CharField(
        label="كلمة المرور الجديدة",
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'اتركها فارغة إذا لا تريد تغييرها',
            'autocomplete': 'new-password',
        })
    )
    new_password2 = forms.CharField(
        label="تأكيد كلمة المرور الجديدة",
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'أعد كتابة كلمة المرور الجديدة',
            'autocomplete': 'new-password',
        })
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'phone']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'الاسم الأول'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم العائلة'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'رقم الهاتف'}),
        }
        labels = {
            'username': 'اسم المستخدم',
            'first_name': 'الاسم الأول',
            'last_name': 'اسم العائلة',
            'phone': 'رقم الهاتف',
        }

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('new_password1')
        p2 = cleaned_data.get('new_password2')
        if p1 or p2:
            if p1 != p2:
                raise forms.ValidationError({'new_password2': 'كلمتا المرور غير متطابقتين.'})
            if p1:
                validate_password(p1, self.instance)
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        p1 = self.cleaned_data.get('new_password1')
        if p1:
            user.set_password(p1)
        if commit:
            user.save()
        return user

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