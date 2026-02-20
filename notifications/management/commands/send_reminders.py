from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from medical.models import ChildVaccineSchedule
from notifications.services import FCMService

class Command(BaseCommand):
    help = 'Sends daily vaccination reminders and missed alerts'

    def handle(self, *args, **options):
        self.stdout.write("Starting notification engine...")
        today = timezone.now().date()
        
        # --- 1. Tomorrow's Reminders (التذكير) ---
        tomorrow = today + timedelta(days=1)
        upcoming_schedules = ChildVaccineSchedule.objects.filter(
            due_date=tomorrow,
            is_taken=False
        ).select_related('child', 'child__family__account', 'vaccine_schedule__vaccine')
        
        reminders_sent = 0
        for schedule in upcoming_schedules:
            family_user = schedule.child.family.account
            if not family_user:
                continue
                
            title = "تذكير بموعد تطعيم 📅"
            body = f"غداً موعد تطعيم طفلك ({schedule.child.full_name}) بلقاح ({schedule.vaccine_schedule.vaccine.name_ar}). يرجى الحضور للمركز."
            
            if FCMService.send_notification(family_user, title, body, notification_type='REMINDER'):
                reminders_sent += 1

        self.stdout.write(self.style.SUCCESS(f"Sent {reminders_sent} REMINDERS for tomorrow."))

        # --- 2. Missed Alerts (المتأخرين - فاتهم الموعد قبل أسبوع) ---
        week_ago = today - timedelta(days=7)
        missed_schedules = ChildVaccineSchedule.objects.filter(
            due_date=week_ago,
            is_taken=False
        ).select_related('child', 'child__family__account', 'vaccine_schedule__vaccine')

        missed_sent = 0
        for schedule in missed_schedules:
            family_user = schedule.child.family.account
            if not family_user:
                continue

            title = "تحذير: تطعيم فائت ⚠️"
            body = f"طفلك ({schedule.child.full_name}) تأخر أسبوعاً عن لقاح ({schedule.vaccine_schedule.vaccine.name_ar}). التأخير قد يضر بصحته!"
            
            if FCMService.send_notification(family_user, title, body, notification_type='MISSED'):
                missed_sent += 1

        self.stdout.write(self.style.WARNING(f"Sent {missed_sent} MISSED ALERTS."))
        self.stdout.write(self.style.SUCCESS("Notification Engine finished."))
