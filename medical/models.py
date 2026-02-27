from django.db import models
from django.conf import settings
from centers.models import Governorate, Directorate, HealthCenter

class Vaccine(models.Model):
    name_ar = models.CharField(max_length=100, verbose_name="اسم اللقاح (عربي)")
    name_en = models.CharField(max_length=100, blank=True, null=True, verbose_name="اسم اللقاح (إنجليزي)")
    description = models.TextField(blank=True, null=True, verbose_name="وصف اللقاح")

    def __str__(self):
        return f"{self.name_ar} / {self.name_en}"

    class Meta:
        verbose_name = "لقاح"
        verbose_name_plural = "اللقاحات"

class VaccineSchedule(models.Model):
    vaccine = models.ForeignKey(Vaccine, on_delete=models.CASCADE, related_name='schedules')
    dose_number = models.PositiveIntegerField(verbose_name="رقم الجرعة")
    age_in_months = models.FloatField(verbose_name="العمر بالأشهر", help_text="0 تعني عند الولادة")
    
    class Meta:
        ordering = ['age_in_months', 'dose_number']
        verbose_name = "جدول اللقاحات"
        verbose_name_plural = "جداول اللقاحات"

    STAGE_CHOICES = (
        ('BASIC', 'أساسي (رضّع)'),
        ('SCHOOL', 'مدرسي (سن المدرسة)'),
    )
    stage = models.CharField(max_length=10, choices=STAGE_CHOICES, default='BASIC', verbose_name="المرحلة")

    def __str__(self):
        if self.stage == 'SCHOOL':
            return f"{self.vaccine.name_ar} - جرعة {self.dose_number} (سن دخول المدرسة)"
        return f"{self.vaccine.name_ar} - جرعة {self.dose_number} (شهر {self.age_in_months})"

# --- الكيانات الجديدة (New Unified Logic) ---

class Family(models.Model):
    """
    جدول العائلة الجديد:
    - يحل محل الأب والأم المنفصلين.
    - الحساب مرتبط به (User).
    - المعرف الفريد هو (اسم الأب + اسم الأم).
    """
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_families', null=True)
    
    # 1. الأسماء (التي تحدد هوية العائلة)
    father_name = models.CharField(max_length=255, verbose_name="اسم الأب الرباعي")
    mother_name = models.CharField(max_length=255, verbose_name="اسم الأم الرباعي")
    
    # 2. الحساب (User Account) - للدخول للتطبيق
    account = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='family_profile', null=True, blank=True)
    access_code = models.CharField("رقم الحساب (ID)", max_length=20, unique=True, editable=False)
    
    notes = models.TextField("ملاحظات", blank=True, null=True)

    class Meta:
        # منع تكرار نفس الأب مع نفس الأم (لأن هذا يعني نفس الحساب)
        # ولكن قد يحدث تشابه أسماء، لذا سنعتمد على الفحص اليدوي في الـ Views أفضل
        # أو يمكننا إضافته هنا كـ UniqueConstraint
        verbose_name = "سجل عائلة"
        verbose_name_plural = "سجلات العائلات"

    def save(self, *args, **kwargs):
        if not self.access_code:
            import random
            from datetime import datetime
            
            while True:
                code_suffix = random.randint(10000, 99999)
                current_year = datetime.now().year
                new_code = f"F-{current_year}-{code_suffix}"
                
                if not Family.objects.filter(access_code=new_code).exists():
                    self.access_code = new_code
                    break
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.access_code} | {self.father_name} & {self.mother_name}"


class Child(models.Model):
    GENDER_CHOICES = (
        ('M', 'ذكر'),
        ('F', 'أنثى'),
    )
    
    # 1. البيانات الأساسية
    full_name = models.CharField(max_length=255, verbose_name="اسم الطفل (الرباعي)")
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, verbose_name="الجنس")
    date_of_birth = models.DateField(verbose_name="تاريخ الميلاد")
    
    # 2. العلاقات (الاهل + المكان)
    family = models.ForeignKey(Family, on_delete=models.PROTECT, related_name='children', verbose_name="العائلة")
    health_center = models.ForeignKey(HealthCenter, on_delete=models.PROTECT, related_name='children', verbose_name="مركز التسجيل", null=True, blank=True)
    
    # مكان الميلاد (للاحصائيات)
    # مكان الميلاد (للاحصائيات)
    birth_governorate = models.ForeignKey(Governorate, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="محافظة الميلاد")
    birth_directorate = models.ForeignKey(Directorate, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="مديرية الميلاد")
    # تم تغيير مكان الميلاد لنصي بناءً على طلب User
    place_of_birth = models.CharField(max_length=255, verbose_name="مكان الميلاد (قرية/منزل/مرفق)")

    # 3. الحالة
    is_completed = models.BooleanField(default=False, verbose_name="مكتمل التحصين (مؤرشف)")
    completed_date = models.DateField(null=True, blank=True, verbose_name="تاريخ الاكتمال")
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_children', null=True)

    def __str__(self):
        return self.full_name

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['family', 'full_name', 'date_of_birth'],
                name='unique_child_registration'
            )
        ]
        verbose_name = "طفل"
        verbose_name_plural = "الأطفال"


class VaccineRecord(models.Model):
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='vaccine_records')
    vaccine = models.ForeignKey(Vaccine, on_delete=models.PROTECT)
    dose_number = models.PositiveIntegerField()
    
    date_given = models.DateField(verbose_name="تاريخ الإعطاء")
    staff = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name="الموظف المسؤول")
    
    # يمكن إضافة حقل "المركز الذي أعطى اللقاح" مستقبلاً
    
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('child', 'vaccine', 'dose_number')
        verbose_name = "سجل تطعيم"
        verbose_name_plural = "سجلات التطعيم"

class ChildVaccineSchedule(models.Model):
    """
    الجدول الزمني الخاص بالطفل (يتم إنشاؤه عند تسجيل الطفل).
    يحتوي على مواعيد الاستحقاق الخاصة بهذا الطفل بناء على تاريخ ميلاده.
    """
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='personal_schedule')
    vaccine_schedule = models.ForeignKey(VaccineSchedule, on_delete=models.CASCADE)
    due_date = models.DateField(verbose_name="تاريخ الاستحقاق")
    is_taken = models.BooleanField(default=False, verbose_name="تم أخذ اللقاح")
    
    def __str__(self):
        return f"{self.child.full_name} - {self.vaccine_schedule} ({self.due_date})"

    class Meta:
        verbose_name = "استحقاق لقاح"
        verbose_name_plural = "استحقاقات اللقاحات"