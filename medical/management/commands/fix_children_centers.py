"""
أمر إدارة لإصلاح health_center للأطفال الذين ليس لديهم مركز محدد.
يبحث في سجلات التطعيم ويعيّن المركز الأول المسجّل للطفل.

الاستخدام:
    python manage.py fix_children_centers
"""
from django.core.management.base import BaseCommand
from medical.models import Child, VaccineRecord


class Command(BaseCommand):
    help = 'إصلاح health_center للأطفال الذين ليس لديهم مركز محدد'

    def handle(self, *args, **options):
        fixed = 0
        skipped = 0

        children_without_center = Child.objects.filter(health_center__isnull=True)
        self.stdout.write(f'الأطفال بدون مركز: {children_without_center.count()}')

        for child in children_without_center:
            # ابحث عن أول جرعة مسجّلة لها مركز
            record = VaccineRecord.objects.filter(
                child=child,
                health_center__isnull=False
            ).order_by('date_given').first()

            if record and record.health_center:
                child.health_center = record.health_center
                child.save(update_fields=['health_center'])
                fixed += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ {child.full_name} → {record.health_center.name_ar}')
                )
            else:
                skipped += 1
                self.stdout.write(
                    self.style.WARNING(f'  ✗ {child.full_name} — لا توجد جرعة مسجّلة بمركز')
                )

        self.stdout.write(self.style.SUCCESS(
            f'\nتم: إصلاح {fixed} طفل، تجاهل {skipped} طفل بدون سجلات.'
        ))
