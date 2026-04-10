from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from .models import Child, VaccineSchedule, ChildVaccineSchedule, Family, VaccineRecord
from dateutil.relativedelta import relativedelta
from datetime import timedelta
from django.utils import timezone

@receiver(post_save, sender=Child)
def generate_child_schedule(sender, instance, created, **kwargs):
    """
    Generate vaccination schedule automatically when a new Child is created.
    This ensures logic is consistent across Admin, API, and Custom Views.
    """
    if created:
        # Check if schedules already exist (to avoid duplication if manually handled elsewhere)
        if ChildVaccineSchedule.objects.filter(child=instance).exists():
            return

        standard_schedules = VaccineSchedule.objects.all()
        personal_schedule_list = []
        
        for item in standard_schedules:
            # Calculate due date
            months_int = int(item.age_in_months)
            days_extra = int((item.age_in_months - months_int) * 30)
            
            # Use instance.date_of_birth
            if instance.date_of_birth:
                due_date = instance.date_of_birth + relativedelta(months=months_int) + timedelta(days=days_extra)
                
                personal_schedule_list.append(
                    ChildVaccineSchedule(
                        child=instance,
                        vaccine_schedule=item,
                        due_date=due_date,
                        is_taken=False
                    )
                )
        
        if personal_schedule_list:
            ChildVaccineSchedule.objects.bulk_create(personal_schedule_list)


@receiver(post_save, sender=Family)
def create_family_user(sender, instance, created, **kwargs):
    """
    إنشاء حساب مستخدم تلقائي للعائلة عند إنشائها.
    اسم المستخدم = كود العائلة
    كلمة المرور = كود العائلة
    """
    if created and not instance.account:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # إنشاء المستخدم
        if instance.access_code:
            user = User.objects.create_user(
                username=instance.access_code,
                password=instance.access_code,
                role='CUSTOMER',  # دور جديد للأهالي
                
                first_name=instance.father_name.split()[0], # الاسم الأول للأب
                last_name=instance.father_name.split()[-1] if len(instance.father_name.split()) > 1 else ""
            )
            
            # ربط الحساب بالعائلة
            instance.account = user
            instance.save()


@receiver(post_save, sender=VaccineRecord)
def sync_vaccine_record_to_child(sender, instance, created, **kwargs):
    """
    عند إضافة أو تعديل سجل تطعيم (VaccineRecord):
    1. نحدث جدول الطفل (ChildVaccineSchedule) لنجعله is_taken = True
    2. نتحقق ما إذا كان الطفل قد أكمل جميع التلقيحات الأساسية (BASIC)
    3. إذا أكمل الأساسي، نحدّث حالة الطفل (is_completed = True)
    """
    child = instance.child
    vaccine = instance.vaccine
    dose = instance.dose_number
    
    # 1. Update ChildVaccineSchedule
    schedule_item = ChildVaccineSchedule.objects.filter(
        child=child,
        vaccine_schedule__vaccine=vaccine,
        vaccine_schedule__dose_number=dose
    ).first()
    
    if schedule_item and not schedule_item.is_taken:
        schedule_item.is_taken = True
        schedule_item.save(update_fields=['is_taken'])
        
    # 2. Check complete status
    all_basic_schedules = ChildVaccineSchedule.objects.filter(
        child=child,
        vaccine_schedule__stage='BASIC'
    )
    
    if all_basic_schedules.exists():
        has_pending_basic = all_basic_schedules.filter(is_taken=False).exists()
        
        if not has_pending_basic and not child.is_completed:
            child.is_completed = True
            child.completed_date = timezone.now().date()
            child.save(update_fields=['is_completed', 'completed_date'])
        elif has_pending_basic and child.is_completed:
            child.is_completed = False
            child.completed_date = None
            child.save(update_fields=['is_completed', 'completed_date'])


@receiver(post_delete, sender=VaccineRecord)
def handle_vaccine_record_deletion(sender, instance, **kwargs):
    """
    عند حذف سجل تطعيم بالخطأ، نعيد حالة الجدول للطفل كغير مكتمل
    """
    child = instance.child
    vaccine = instance.vaccine
    dose = instance.dose_number
    
    # 1. Revert ChildVaccineSchedule
    schedule_item = ChildVaccineSchedule.objects.filter(
        child=child,
        vaccine_schedule__vaccine=vaccine,
        vaccine_schedule__dose_number=dose
    ).first()
    
    if schedule_item and schedule_item.is_taken:
        schedule_item.is_taken = False
        schedule_item.save(update_fields=['is_taken'])
        
    # 2. Check complete status
    if child.is_completed:
        all_basic_schedules = ChildVaccineSchedule.objects.filter(
            child=child,
            vaccine_schedule__stage='BASIC'
        )
        if all_basic_schedules.filter(is_taken=False).exists():
            child.is_completed = False
            child.completed_date = None
            child.save(update_fields=['is_completed', 'completed_date'])

@receiver(post_save, sender=VaccineSchedule)
def backfill_vaccine_schedule(sender, instance, created, **kwargs):
    """
    عند إضافة جرعة لقاح جديدة (VaccineSchedule):
    نقوم بإضافتها تلقائياً لجميع الأطفال الحاليين في النظام
    بشرط أن لا يكون عمر الطفل قد تجاوز العمر المحدد للجرعة.
    """
    if created:
        today = timezone.now().date()
        months_int = int(instance.age_in_months)
        days_extra = int((instance.age_in_months - months_int) * 30)
        
        personal_schedule_list = []
        
        # جلب جميع الأطفال الذين لديهم تاريخ ميلاد
        children = Child.objects.filter(date_of_birth__isnull=False)
        
        for child in children:
            due_date = child.date_of_birth + relativedelta(months=months_int) + timedelta(days=days_extra)
            
            # إذا كان تاريخ الاستحقاق اليوم أو في المستقبل (أي أن الطفل لم يتجاوز العمر المطلوب)
            if due_date >= today:
                personal_schedule_list.append(
                    ChildVaccineSchedule(
                        child=child,
                        vaccine_schedule=instance,
                        due_date=due_date,
                        is_taken=False
                    )
                )
                
        # حفظ السجلات دفعة واحدة في قاعدة البيانات لتحسين الأداء
        if personal_schedule_list:
            ChildVaccineSchedule.objects.bulk_create(personal_schedule_list)


@receiver(pre_delete, sender=Child)
def cleanup_family_if_last_child(sender, instance, **kwargs):
    """
    عند حذف طفل:
    - نتحقق إذا كان الطفل هو الوحيد في العائلة
    - إذا نعم: نحذف حساب المستخدم المرتبط بالعائلة ثم نحذف العائلة تلقائياً
    - إذا لا: نترك العائلة كما هي (لا يزال فيها أطفال آخرون)
    """
    family = instance.family
    if not family:
        return

    # نحسب الأطفال المتبقين بعد الحذف (نستثني الطفل الحالي)
    remaining_children = Child.objects.filter(family=family).exclude(pk=instance.pk).count()

    if remaining_children == 0:
        # الطفل هو الأخير في العائلة — نحذف حساب المستخدم والعائلة
        user_account = family.account
        if user_account:
            user_account.delete()  # حذف الحساب أولاً لتجنب أخطاء المفاتيح الخارجية
        family.delete()  # ثم حذف العائلة
