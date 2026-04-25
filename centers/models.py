from django.db import models
from django.conf import settings  # لاستدعاء موديل اليوزر بطريقة آمنة

class Governorate(models.Model):
    name_ar = models.CharField(max_length=100, verbose_name="اسم المحافظة (عربي)")
    name_en = models.CharField(max_length=100, blank=True, null=True, verbose_name="اسم المحافظة (إنجليزي)")
    code = models.CharField(max_length=5, unique=True, verbose_name="كود المحافظة", help_text="مثلاً 14 لإب")

    def __str__(self):
        return f"{self.name_ar} ({self.code})"

    class Meta:
        verbose_name = "محافظة"
        verbose_name_plural = "المحافظات"

class Directorate(models.Model):
    governorate = models.ForeignKey(Governorate, on_delete=models.CASCADE, related_name='directorates', verbose_name="المحافظة")
    name_ar = models.CharField(max_length=100, verbose_name="اسم المديرية (عربي)")
    name_en = models.CharField(max_length=100, blank=True, null=True, verbose_name="اسم المديرية (إنجليزي)")
    code = models.CharField(max_length=5, verbose_name="كود المديرية", help_text="مثلاً 01 للمشنة")

    class Meta:
        unique_together = ('governorate', 'code')
        verbose_name = "مديرية"
        verbose_name_plural = "المديريات"

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
    WORKING_HOURS_CHOICES = (
        ('فترة صباحية (8:00 ص - 1:00 م)', 'فترة صباحية (8:00 ص - 1:00 م)'),
        ('فترة مسائية (4:00 م - 9:00 م)', 'فترة مسائية (4:00 م - 9:00 م)'),
        ('فترتين (8 ص - 1 م / 4 م - 9 م)', 'فترتين (8 ص - 1 م / 4 م - 9 م)'),
        ('على مدار الساعة (24/7)', 'على مدار الساعة (24/7)')
    )
    working_hours = models.CharField(max_length=255, choices=WORKING_HOURS_CHOICES, blank=True, null=True, verbose_name="ساعات العمل")

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

    class Meta:
        verbose_name = "مركز صحي"
        verbose_name_plural = "المراكز الصحية"
        unique_together = ('name_ar', 'governorate', 'directorate')

class CenterComplaint(models.Model):
    COMPLAINT_TYPES = (
        ('EXCELLENT',            'ممتاز - خدمة رائعة'),
        ('GOOD',                 'جيد - لا توجد ملاحظات'),
        ('VACCINE_UNAVAILABLE',  'اللقاح غير متوفر بالمركز'),
        ('SUBSTITUTE_GIVEN',     'تم إعطاء لقاح بديل'),
        ('ILLEGAL_FEES',         'طُلبت رسوم مالية غير قانونية'),
        ('BAD_TREATMENT',        'سوء المعاملة'),
        ('STAFF_ABSENT',         'غياب الموظفين'),
        ('OTHER',                'أخرى'),
    )

    STATUS_CHOICES = (
        ('PENDING',    'قيد المراجعة'),
        ('REVIEWED',   'تمت المراجعة'),
        ('RESOLVED',   'تم الحل'),
    )

    STARS_CHOICES = [(i, f'{i} نجمة') for i in range(1, 6)]

    # الروابط
    vaccine_record = models.OneToOneField(
        'medical.VaccineRecord',
        on_delete=models.CASCADE,
        related_name='complaint',
        verbose_name="سجل التطعيم",
        null=True,
        blank=True
    )
    health_center = models.ForeignKey(
        HealthCenter,
        on_delete=models.PROTECT,
        related_name='complaints',
        verbose_name="المركز المُبلَّغ عنه"
    )
    family = models.ForeignKey(
        'medical.Family',
        on_delete=models.CASCADE,
        related_name='complaints',
        verbose_name="العائلة"
    )

    # ── حقل التقييم الجديد (نجوم 1-5) ──────────────────────────────
    stars = models.IntegerField(
        choices=STARS_CHOICES,
        null=True,
        blank=True,
        verbose_name="التقييم بالنجوم"
    )

    # بيانات الشكوى (complaint_type محتفظ به للبيانات القديمة)
    complaint_type = models.CharField(
        max_length=25,
        choices=COMPLAINT_TYPES,
        verbose_name="نوع الشكوى",
        null=True,
        blank=True,
    )
    details = models.TextField(blank=True, null=True, verbose_name="تعليق / تفاصيل إضافية")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "تقييم مركز"
        verbose_name_plural = "تقييمات المراكز"

    def __str__(self):
        stars_str = f"{self.stars}⭐" if self.stars else self.get_complaint_type_display()
        return f"{stars_str} — {self.health_center.name_ar}"
