
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from medical.models import VaccineSchedule, Child, ChildVaccineSchedule
from django.utils import timezone

# 1. Update 6-year vaccines to SCHOOL stage
updated_count = VaccineSchedule.objects.filter(age_in_months__gte=72).update(stage='SCHOOL')
print(f"Updated {updated_count} vaccine schedules to 'SCHOOL' stage.")

# 2. Re-evaluate all incomplete children
children = Child.objects.filter(is_completed=False)
archived_count = 0

print(f"Checking {children.count()} active children...")

for child in children:
    # Check if they have any pending BASIC vaccines
    remaining_basic = ChildVaccineSchedule.objects.filter(
        child=child, 
        is_taken=False,
        vaccine_schedule__stage='BASIC'  # The new condition
    ).count()
    
    if remaining_basic == 0:
        print(f" - Archiving child: {child.full_name}")
        child.is_completed = True
        child.completed_date = timezone.now().date()
        child.save()
        archived_count += 1

print(f"Successfully archived {archived_count} children.")
