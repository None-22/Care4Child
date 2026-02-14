import os
import sys
import django

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from medical.models import Vaccine, VaccineSchedule, VaccineRecord, ChildVaccineSchedule

def populate_vaccines():
    # 1. Clear existing data (Deep Clean to avoid ProtectedError)
    print("Cleaning old vaccine data...")
    VaccineRecord.objects.all().delete() # Delete actual records
    ChildVaccineSchedule.objects.all().delete() # Delete planned schedules
    VaccineSchedule.objects.all().delete() # Delete master schedule
    Vaccine.objects.all().delete() # Delete vaccines

    # 2. Define Vaccines based on the "Ideal Childhood Immunization Schedule" Image
    vaccines_data = [
        {"name_ar": "السل (BCG)", "name_en": "BCG", "description": "يؤخذ عند الولادة (الذراع الأيسر)"},
        {"name_ar": "التهاب الكبد البائي (Hep B)", "name_en": "Hepatitis B", "description": "جرعة واحدة عند الولادة"},
        {"name_ar": "شلل الأطفال الفموي (OPV)", "name_en": "OPV", "description": "قطرات بالفم"},
        {"name_ar": "الخماسي (Penta)", "name_en": "Pentavalent", "description": "دفتيريا، كزاز، سعال ديكي، كبد ب، هيب"},
        {"name_ar": "المكورات الرئوية (PCV)", "name_en": "Pneumococcal", "description": "ضد الالتهاب الرئوي"},
        {"name_ar": "الروتا (Rota)", "name_en": "Rotavirus", "description": "ضد الإسهالات"},
        {"name_ar": "شلل الأطفال الحقن (IPV)", "name_en": "IPV", "description": "حقنة عضلية"},
        {"name_ar": "الحصبة والحصبة الألمانية (MR)", "name_en": "Measles/Rubella", "description": "حقنة تحت الجلد"},
        {"name_ar": "فيتامين أ (Vit A)", "name_en": "Vitamin A", "description": "كبسولة"},
        {"name_ar": "الثنائي (TD)", "name_en": "TD", "description": "كزاز ودفتيريا (للكبار)"},
    ]

    print("Creating Vaccines...")
    vaccine_objs = {}
    for v_data in vaccines_data:
        vac = Vaccine.objects.create(**v_data)
        vaccine_objs[v_data['name_en']] = vac
        print(f"- Created {vac.name_ar}")

    # 3. Define Schedule (Doses & Ages)
    schedule_data = [
        # --- At Birth (0 months) ---
        {"vaccine": "BCG", "dose": 1, "age": 0},
        {"vaccine": "Hepatitis B", "dose": 1, "age": 0},
        {"vaccine": "OPV", "dose": 0, "age": 0}, # Zero dose

        # --- 1.5 Months (6 Weeks) ---
        {"vaccine": "OPV", "dose": 1, "age": 1.5},
        {"vaccine": "Pentavalent", "dose": 1, "age": 1.5},
        {"vaccine": "Pneumococcal", "dose": 1, "age": 1.5},
        {"vaccine": "Rotavirus", "dose": 1, "age": 1.5},

        # --- 2.5 Months (10 Weeks) ---
        {"vaccine": "OPV", "dose": 2, "age": 2.5},
        {"vaccine": "Pentavalent", "dose": 2, "age": 2.5},
        {"vaccine": "Pneumococcal", "dose": 2, "age": 2.5},
        {"vaccine": "Rotavirus", "dose": 2, "age": 2.5},

        # --- 3.5 Months (14 Weeks) ---
        {"vaccine": "OPV", "dose": 3, "age": 3.5},
        {"vaccine": "Pentavalent", "dose": 3, "age": 3.5},
        {"vaccine": "Pneumococcal", "dose": 3, "age": 3.5},
        {"vaccine": "IPV", "dose": 1, "age": 3.5},

        # --- 9 Months ---
        {"vaccine": "Measles/Rubella", "dose": 1, "age": 9},
        {"vaccine": "OPV", "dose": 4, "age": 9},
        {"vaccine": "IPV", "dose": 2, "age": 9},
        {"vaccine": "Vitamin A", "dose": 1, "age": 9},

        # --- 18 Months (1.5 Years) ---
        {"vaccine": "Measles/Rubella", "dose": 2, "age": 18},
        {"vaccine": "OPV", "dose": 5, "age": 18},
        {"vaccine": "Vitamin A", "dose": 2, "age": 18},
        {"vaccine": "Pentavalent", "dose": 4, "age": 18}, # Booster (جرعة تنشيطية) - let's call it dose 4

        # --- School Entry (approx 6 years = 72 months) ---
        # Note: Setting age to 72 months for sorting purposes
        {"vaccine": "Measles/Rubella", "dose": 3, "age": 72}, # Booster
        {"vaccine": "Vitamin A", "dose": 3, "age": 72},
        {"vaccine": "TD", "dose": 1, "age": 72},
    ]

    print("\nCreating Schedule...")
    for sch in schedule_data:
        vac_obj = vaccine_objs[sch['vaccine']]
        VaccineSchedule.objects.create(
            vaccine=vac_obj,
            dose_number=sch['dose'],
            age_in_months=sch['age']
        )
        print(f"- Scheduled {vac_obj.name_ar} (Dose {sch['dose']}) at {sch['age']} months")

    print("\n✅ Database populated successfully with the OFFICIAL schedule!")

if __name__ == '__main__':
    populate_vaccines()
