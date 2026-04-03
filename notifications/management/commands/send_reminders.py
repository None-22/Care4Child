from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from medical.models import ChildVaccineSchedule
from notifications.services import FCMService

class Command(BaseCommand):
    help = 'Sends vaccination reminders (3, 2, 1 days before) and missed alerts (1 day after)'

    def handle(self, *args, **options):
        self.stdout.write("Starting notification engine...")
        today = timezone.now().date()
        
        # --- 1. Reminders (قبل 3 أيام، ويومين، ويوم واحد) ---
        reminder_days = [3, 2, 1]
        reminders_sent = 0
        
        for days_ahead in reminder_days:
            target_date = today + timedelta(days=days_ahead)
            upcoming_schedules = ChildVaccineSchedule.objects.filter(
                due_date=target_date,
                is_taken=False
            ).select_related('child', 'child__family__account', 'vaccine_schedule__vaccine')
            
            for schedule in upcoming_schedules:
                family_user = schedule.child.family.account
                if not family_user:
                    continue
                    
                title = "تذكير بموعد تطعيم"
                if days_ahead == 1:
                    day_text = "غداً"
                elif days_ahead == 2:
                    day_text = "بعد غدٍ"
                else:
                    day_text = f"بعد {days_ahead} أيام"
                    
                body = f"تذكير: موعد تطعيم طفلك ({schedule.child.full_name}) بلقاح ({schedule.vaccine_schedule.vaccine.name_ar}) سيكون {day_text}. يرجى الحضور للمركز."
                
                if FCMService.send_notification(family_user, title, body, notification_type='REMINDER'):
                    reminders_sent += 1

        self.stdout.write(self.style.SUCCESS(f"Sent {reminders_sent} REMINDERS in total."))

        # --- 2. Missed Alerts (المتأخرين - فاتهم الموعد بيوم واحد فقط) ---
        yesterday = today - timedelta(days=1)
        missed_schedules = ChildVaccineSchedule.objects.filter(
            due_date=yesterday,
            is_taken=False
        ).select_related('child', 'child__family__account', 'vaccine_schedule__vaccine')

        missed_sent = 0
        for schedule in missed_schedules:
            family_user = schedule.child.family.account
            if not family_user:
                continue

            title = "تحذير: تطعيم فائت"
            body = f"طفلك ({schedule.child.full_name}) قد فاته موعد لقاح ({schedule.vaccine_schedule.vaccine.name_ar}) يوم أمس. يرجى التوجه للمركز بأقرب وقت!"
            
            if FCMService.send_notification(family_user, title, body, notification_type='MISSED'):
                missed_sent += 1

        self.stdout.write(self.style.WARNING(f"Sent {missed_sent} MISSED ALERTS."))
        self.stdout.write(self.style.SUCCESS("Notification Engine finished."))