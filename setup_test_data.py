# Setup Test Data Script
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.contrib.auth import get_user_model
from centers.models import Governorate, Directorate, HealthCenter
from medical.models import Family, Child
from datetime import date

User = get_user_model()

# 1. Create Superuser if not exists
if not User.objects.filter(username='admin').exists():
    admin = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print("Superuser 'admin' created.")
else:
    admin = User.objects.get(username='admin')
    print("Superuser 'admin' exists.")

# 2. Create Location Data
gov, _ = Governorate.objects.get_or_create(name_ar='Ibb', code='14')
dir_obj, _ = Directorate.objects.get_or_create(name_ar='Al-Mashannah', code='01', governorate=gov)

# 3. Create Health Center
center, _ = HealthCenter.objects.get_or_create(
    name_ar='Test Center',
    defaults={
        'governorate': gov,
        'directorate': dir_obj,
        'address': 'Test Address',
        'is_active': True
    }
)
print(f"Health Center '{center.name_ar}' ready.")

# Ensure admin has a health center (if the user model requires/supports it for logic)
if hasattr(admin, 'health_center'):
    admin.health_center = center
    admin.save()

# 4. Create Family
family, _ = Family.objects.get_or_create(
    father_name='Test Father',
    mother_name='Test Mother',
    defaults={
        'access_code': 'F-Test-01',
        'created_by': admin
    }
)

# 5. Create Child
child, created = Child.objects.get_or_create(
    full_name='Test Child',
    defaults={
        'gender': 'M',
        'date_of_birth': date(2024, 1, 1),
        'family': family,
        'health_center': center,
        # KEY FIELDS TO TEST:
        'birth_governorate': gov,
        'birth_directorate': dir_obj,
        'birth_health_center': center,
        'place_of_birth_detail': 'Hospital',
        'created_by': admin
    }
)
print(f"Child '{child.full_name}' ready. ID: {child.id}")
