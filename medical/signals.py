from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Child, VaccineSchedule, ChildVaccineSchedule, Family
from dateutil.relativedelta import relativedelta
from datetime import timedelta

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
                last_name="Family"
            )
            
            # ربط الحساب بالعائلة
            instance.account = user
            instance.save()
