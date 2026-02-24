from django.contrib import admin
from .models import Governorate, Directorate, HealthCenter

@admin.register(Governorate)
class GovernorateAdmin(admin.ModelAdmin):
    list_display = ('name_ar', 'code')
    search_fields = ('name_ar', 'code')

@admin.register(Directorate)
class DirectorateAdmin(admin.ModelAdmin):
    list_display = ('name_ar', 'governorate', 'code')
    list_filter = ('governorate',)
    search_fields = ('name_ar', 'code')

from django import forms
from django.contrib.auth import get_user_model
from django.contrib import messages

User = get_user_model()

class HealthCenterForm(forms.ModelForm):
    manager_password = forms.CharField(
        label="كلمة مرور المدير",
        widget=forms.PasswordInput,
        required=False,
        help_text="عند إضافة مركز جديد، أدخل كلمة المرور هنا لإنشاء حساب مدير تلقائياً (اسم المستخدم سيكون اسم المركز)."
    )

    class Meta:
        model = HealthCenter
        fields = '__all__'

@admin.register(HealthCenter)
class HealthCenterAdmin(admin.ModelAdmin):
    form = HealthCenterForm
    list_display = ('name_ar', 'center_code', 'governorate', 'directorate', 'is_active')
    list_filter = ('governorate', 'is_active')
    search_fields = ('name_ar', 'center_code')
    readonly_fields = ('center_code',) 

    class Media:
        js = (
            'smart-selects/admin/js/chainedfk.js',
            'smart-selects/admin/js/bindfields.js',
        )

    def save_model(self, request, obj, form, change):
        is_new = obj.pk is None
        super().save_model(request, obj, form, change)
        
        # Auto-create User Logic
        password = form.cleaned_data.get('manager_password')
        
        if password:
            try:
                # Use Center Name as Username (Spaces -> Underscores)
                username = obj.name_ar.strip()
                
                user, created = User.objects.get_or_create(username=username)
                
                user.set_password(password)
                user.role = 'CENTER_MANAGER'
                user.health_center = obj
                user.save()
                
                msg = f"تم {'إنشاء' if created else 'تحديث'} حساب مدير المركز بنجاح. اسم المستخدم: {username}"
                messages.success(request, msg)
            except Exception as e:
                messages.error(request, f"حدث خطأ أثناء إنشاء المستخدم: {e}")
        elif is_new and not password:
            messages.warning(request, "لم يتم إنشاء حساب مستخدم للمركز لأنك لم تدخل كلمة المرور.")
 