from django.db import models
from django.conf import settings  # لاستدعاء موديل اليوزر بطريقة آمنة

class Governorate(models.Model):
    name_ar = models.CharField(max_length=100, verbose_name="اسم المحافظة (عربي)")
    name_en = models.CharField(max_length=100, blank=True, null=True, verbose_name="اسم المحافظة (إنجليزي)")
    code = models.CharField(max_length=5, unique=True, verbose_name="كود المحافظة", help_text="مثلاً 14 لإب")

    def __str__(self):
        return f"{self.name_ar} ({self.code})"

class Directorate(models.Model):
    governorate = models.ForeignKey(Governorate, on_delete=models.CASCADE, related_name='directorates', verbose_name="المحافظة")
    name_ar = models.CharField(max_length=100, verbose_name="اسم المديرية (عربي)")
    name_en = models.CharField(max_length=100, blank=True, null=True, verbose_name="اسم المديرية (إنجليزي)")
    code = models.CharField(max_length=5, verbose_name="كود المديرية", help_text="مثلاً 01 للمشنة")

    class Meta:
        unique_together = ('governorate', 'code')

    def __str__(self):
        return f"{self.name_ar} ({self.code})"

from smart_selects.db_fields import ChainedForeignKey

# ...

class HealthCenter(models.Model):
    # الموقع الإداري
    governorate = models.ForeignKey(Governorate, on_delete=models.PROTECT, verbose_name="المحافظة", null=True, blank=True)
    directorate = ChainedForeignKey(
        Directorate,
        chained_field="governorate",
        chained_model_field="governorate",
        show_all=False,
        auto_choose=True,
        sort=True,
        verbose_name="المديرية",
        null=True, blank=True
    )
    
    # الكود المولد تلقائياً
    center_code = models.CharField(max_length=20, unique=True, verbose_name="كود المركز", editable=False, blank=True)
    
    # بيانات المركز الأساسية
    name_ar = models.CharField(max_length=255, verbose_name="اسم المركز (عربي)")
    name_en = models.CharField(max_length=255, blank=True, null=True, verbose_name="اسم المركز (إنجليزي)")
    # city = removed as redundant
    address = models.TextField(verbose_name="العنوان التفصيلي")
    working_hours = models.CharField(max_length=255, blank=True, null=True, verbose_name="ساعات العمل")

    # حقول إدارية
    license_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="رقم الترخيص", help_text="رقم آخر غير كود المركز")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.center_code and self.governorate and self.directorate:
            # Generate Code: GovCode + DirCode + 4-digit Serial
            prefix = f"{self.governorate.code}{self.directorate.code}"
            
            # Find last center in this dir to increment
            last_center = HealthCenter.objects.filter(
                governorate=self.governorate, 
                directorate=self.directorate
            ).order_by('center_code').last()
            
            if last_center and last_center.center_code.startswith(prefix):
                try:
                    last_seq = int(last_center.center_code[len(prefix):])
                    new_seq = last_seq + 1
                except ValueError:
                    new_seq = 1
            else:
                new_seq = 1
            
            self.center_code = f"{prefix}{new_seq:04d}"
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name_ar} ({self.center_code})"

