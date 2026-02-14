from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models

class CustomUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('role', 'ADMIN')
        return super().create_superuser(username, email, password, **extra_fields)

class CustomUser(AbstractUser):
    objects = CustomUserManager()
    # أنواع المستخدمين
    USER_TYPE_CHOICES = (
        ('ADMIN', 'مدير النظام'),        # الوزارة/المبرمج
        ('CENTER_MANAGER', 'مدير مركز'), # مدير المركز (جديد)
        ('CENTER_STAFF', 'موظف مركز'),   # الموظف داخل المركز
        ('CUSTOMER', 'ولي أمر'),         # (اختياري)
    )
    
    role = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='CENTER_STAFF', verbose_name="نوع الحساب")
    
    # ربط الموظف بالمركز (علاقة مباشرة لأن الموظف يتبع مركزاً واحداً فقط)
    health_center = models.ForeignKey('centers.HealthCenter', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="المركز الصحي", related_name="staff_members")
    
    # بيانات إضافية
    phone = models.CharField(max_length=15, blank=True, null=True, verbose_name="رقم الهاتف")

    def __str__(self):
        if self.health_center:
            return f"{self.username} - {self.health_center.name_ar}"
        return self.username

    @property
    def is_center_manager(self):
        return self.role == 'CENTER_MANAGER'

    @property
    def is_center_staff(self):
        return self.role == 'CENTER_STAFF'