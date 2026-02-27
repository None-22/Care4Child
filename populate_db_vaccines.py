import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from medical.models import Vaccine, VaccineSchedule

def run():
    print("Start populating vaccines...")
    # Clear existing to prevent duplicates if run multiple times
    VaccineSchedule.objects.all().delete()
    Vaccine.objects.all().delete()

    vaccines_data = {
        'BCG': {'ar': 'لقاح الدرن (السل)', 'en': 'BCG'},
        'HepB': {'ar': 'لقاح الكبد البائي', 'en': 'Hepatitis B'},
        'OPV': {'ar': 'لقاح الشلل الفموي', 'en': 'OPV'},
        'Penta': {'ar': 'اللقاح الخماسي', 'en': 'Pentavalent'},
        'Pneumo': {'ar': 'لقاح المكورات الرئوية', 'en': 'Pneumococcal'},
        'ROTA': {'ar': 'لقاح الروتا', 'en': 'ROTA'},
        'IPV': {'ar': 'لقاح الشلل الحقن', 'en': 'IPV'},
        'MR': {'ar': 'لقاح الحصبة والحصبة الألمانية', 'en': 'MR'},
        'VitA': {'ar': 'فيتامين (أ)', 'en': 'Vitamin A'},
        'TD': {'ar': 'اللقاح الثنائي', 'en': 'TD'},
    }

    v_objs = {}
    for key, data in vaccines_data.items():
        v, _ = Vaccine.objects.get_or_create(
            name_en=data['en'],
            defaults={'name_ar': data['ar']}
        )
        v.name_ar = data['ar']
        v.save()
        v_objs[key] = v

    schedules_data = [
        # At Birth (0 months)
        (v_objs['BCG'], 1, 0, 'BASIC'),
        (v_objs['HepB'], 1, 0, 'BASIC'),
        (v_objs['OPV'], 0, 0, 'BASIC'), # Dose 0 (التمهيدي)

        # 1.5 months
        (v_objs['OPV'], 1, 1.5, 'BASIC'),
        (v_objs['Penta'], 1, 1.5, 'BASIC'),
        (v_objs['Pneumo'], 1, 1.5, 'BASIC'),
        (v_objs['ROTA'], 1, 1.5, 'BASIC'),

        # 2.5 months
        (v_objs['OPV'], 2, 2.5, 'BASIC'),
        (v_objs['Penta'], 2, 2.5, 'BASIC'),
        (v_objs['Pneumo'], 2, 2.5, 'BASIC'),
        (v_objs['ROTA'], 2, 2.5, 'BASIC'),

        # 3.5 months
        (v_objs['OPV'], 3, 3.5, 'BASIC'),
        (v_objs['Penta'], 3, 3.5, 'BASIC'),
        (v_objs['Pneumo'], 3, 3.5, 'BASIC'),
        (v_objs['IPV'], 1, 3.5, 'BASIC'),

        # 9 months
        (v_objs['MR'], 1, 9, 'BASIC'),
        (v_objs['OPV'], 4, 9, 'BASIC'),
        (v_objs['IPV'], 2, 9, 'BASIC'),
        (v_objs['VitA'], 1, 9, 'BASIC'),

        # 18 months
        (v_objs['MR'], 2, 18, 'BASIC'),
        (v_objs['OPV'], 5, 18, 'BASIC'),
        (v_objs['VitA'], 2, 18, 'BASIC'),
        (v_objs['Penta'], 4, 18, 'BASIC'),

        # School Age (~60 months = 5 years)
        (v_objs['MR'], 3, 60, 'SCHOOL'), # الجرعة التنشيطية
        (v_objs['VitA'], 3, 60, 'SCHOOL'),
        (v_objs['TD'], 1, 60, 'SCHOOL'),
    ]

    for v, dose, age, stage in schedules_data:
        VaccineSchedule.objects.create(
            vaccine=v,
            dose_number=dose,
            age_in_months=age,
            stage=stage
        )

    print("Successfully populated standard Yemen vaccines!")

if __name__ == '__main__':
    run()
