from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

# تسجيل موديل المستخدم الجديد في لوحة التحكم
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    # نضيف الحقول الجديدة لتظهر في الداشبورد
  
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('المعلومات الشخصية', {'fields': ('first_name', 'last_name')}), # تم حذف email
        ('بيانات المركز', {'fields': ('role', 'health_center', 'phone')}),
        ('الإشعارات', {'fields': ('fcm_token',)}),
        ('الصلاحيات', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('تواريخ هامة', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('بيانات المركز', {'fields': ('role', 'health_center', 'phone')}),
    )
    
    list_display = ('username', 'role', 'health_center', 'is_staff')
    list_filter = ('role', 'health_center', 'is_staff', 'is_superuser')

admin.site.register(CustomUser, CustomUserAdmin)