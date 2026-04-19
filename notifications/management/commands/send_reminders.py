from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from collections import defaultdict
from medical.models import ChildVaccineSchedule
from notifications.services import FCMService


def age_to_arabic(age_in_months: float) -> str:
    """تحويل العمر بالأشهر لنص عربي مفهوم"""
    if age_in_months == 0:
        return "عند الولادة"
    elif age_in_months == 0.5:
        return "أسبوعين"
    elif age_in_months == 1:
        return "شهر"
    elif age_in_months == 1.5:
        return "شهر ونصف"
    elif age_in_months == 2:
        return "شهرين"
    elif age_in_months == 3:
        return "3 أشهر"
    elif age_in_months == 4:
        return "4 أشهر"
    elif age_in_months == 6:
        return "6 أشهر"
    elif age_in_months == 9:
        return "9 أشهر"
    elif age_in_months == 12:
        return "سنة"
    elif age_in_months == 18:
        return "سنة ونصف"
    elif age_in_months == 24:
        return "سنتين"
    else:
        # تحويل عام: x.0 → "x شهراً"
        if age_in_months == int(age_in_months):
            return f"{int(age_in_months)} شهراً"
        return f"{age_in_months} شهر"


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

            # ✅ تجميع اللقاحات حسب (المستخدم، الطفل، العمر) لإرسال إشعار واحد لكل (طفل + عمر)
            grouped = defaultdict(list)
            for schedule in upcoming_schedules:
                family_user = schedule.child.family.account
                if not family_user:
                    continue
                # المفتاح يشمل العمر لضمان إشعار واحد فقط لكل (طفل + عمر) في نفس اليوم
                key = (family_user.id, schedule.child.id, schedule.vaccine_schedule.age_in_months)
                grouped[key].append({
                    'user': family_user,
                    'child': schedule.child,
                    'vaccine_name': schedule.vaccine_schedule.vaccine.name_ar,
                    'age_in_months': schedule.vaccine_schedule.age_in_months,
                })

            for (user_id, child_id, age_in_months), items in grouped.items():
                family_user = items[0]['user']
                child = items[0]['child']
                vaccine_names = [item['vaccine_name'] for item in items]

                # نص الإشعار المجمّع
                if days_ahead == 1:
                    day_text = "غداً"
                elif days_ahead == 2:
                    day_text = "بعد غدٍ"
                else:
                    day_text = f"بعد {days_ahead} أيام"

                # العمر محدد من المفتاح نفسه (ضمان الدقة)
                age_text = age_to_arabic(age_in_months)
                title = f"تذكير: تطعيمات عمر {age_text} - {child.full_name}"

                vaccines_text = "، ".join(vaccine_names)
                if len(vaccine_names) == 1:
                    body = (
                        f"تذكير: موعد تطعيم طفلك ({child.full_name}) "
                        f"بلقاح ({vaccines_text}) المقرر لعمر {age_text} سيكون {day_text}. "
                        f"يرجى الحضور للمركز الصحي."
                    )
                else:
                    body = (
                        f"تذكير: طفلك ({child.full_name}) لديه {len(vaccine_names)} لقاحات "
                        f"مقررة لعمر {age_text} {day_text}: {vaccines_text}. "
                        f"يرجى الحضور للمركز الصحي."
                    )

                if FCMService.send_notification(
                    family_user, title, body,
                    notification_type='REMINDER',
                    data={'route': 'notifications'},
                ):
                    reminders_sent += 1

        self.stdout.write(self.style.SUCCESS(f"Sent {reminders_sent} REMINDERS in total."))

        # --- 2. Missed Alerts (المتأخرين - فاتهم الموعد بيوم واحد فقط) ---
        yesterday = today - timedelta(days=1)
        missed_schedules = ChildVaccineSchedule.objects.filter(
            due_date=yesterday,
            is_taken=False
        ).select_related('child', 'child__family__account', 'vaccine_schedule__vaccine')

        # ✅ تجميع اللقاحات الفائتة حسب (المستخدم، الطفل، العمر) - إشعار واحد لكل (طفل + عمر)
        grouped_missed = defaultdict(list)
        for schedule in missed_schedules:
            family_user = schedule.child.family.account
            if not family_user:
                continue
            key = (family_user.id, schedule.child.id, schedule.vaccine_schedule.age_in_months)
            grouped_missed[key].append({
                'user': family_user,
                'child': schedule.child,
                'vaccine_name': schedule.vaccine_schedule.vaccine.name_ar,
                'age_in_months': schedule.vaccine_schedule.age_in_months,
            })

        missed_sent = 0
        for (user_id, child_id, age_in_months), items in grouped_missed.items():
            family_user = items[0]['user']
            child = items[0]['child']
            vaccine_names = [item['vaccine_name'] for item in items]

            age_text = age_to_arabic(age_in_months)
            title = f"تحذير: فات موعد تطعيمات عمر {age_text} - {child.full_name}"

            vaccines_text = "، ".join(vaccine_names)
            if len(vaccine_names) == 1:
                body = (
                    f"طفلك ({child.full_name}) قد فاته موعد لقاح ({vaccines_text}) "
                    f"المقرر لعمر {age_text} يوم أمس. يرجى التوجه للمركز بأقرب وقت!"
                )
            else:
                body = (
                    f"طفلك ({child.full_name}) قد فاته {len(vaccine_names)} لقاحات مقررة "
                    f"لعمر {age_text} يوم أمس: {vaccines_text}. يرجى التوجه للمركز بأقرب وقت!"
                )

            if FCMService.send_notification(
                family_user, title, body,
                notification_type='MISSED',
                data={'route': 'notifications'},
            ):
                missed_sent += 1

        self.stdout.write(self.style.WARNING(f"Sent {missed_sent} MISSED ALERTS."))
        self.stdout.write(self.style.SUCCESS("Notification Engine finished."))