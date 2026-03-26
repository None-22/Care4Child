import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from medical.models import Vaccine, VaccineSchedule

def run():
    print("Start populating vaccines with rich data...")
    # Do not delete Vaccines to avoid ProtectedError with VaccineRecord
    VaccineSchedule.objects.all().delete()

    # Medium Data from Flutter App mapped to Backend Struct
    vaccines_info = {
        'BCG': {
            'name_ar': 'لقاح السل (BCG)',
            'name_en': 'Bacillus Calmette-Guérin',
            'desc': 'يحمي من مرض السل الرئوي والتهاب السحايا، ويُعطى بجرعة تمهيدية واحدة (حقن في الكتف الأيسر).'
        },
        'HepB': {
            'name_ar': 'لقاح الكبد البائي (Hep B)',
            'name_en': 'Hepatitis B Vaccine',
            'desc': 'يوفر لمناعة الطفل حماية مبكرة ضد فيروس التهاب الكبد البائي الخطير، ويُعطى عند الولادة مباشرة.'
        },
        'OPV': {
            'name_ar': 'لقاح شلل الأطفال الفموي (OPV)',
            'name_en': 'Oral Polio Vaccine',
            'desc': 'قطرات فموية آمنة توفر مناعة قوية في الأمعاء وتحمي الطفل من أخطار الشلل الدائم.'
        },
        'IPV': {
            'name_ar': 'لقاح شلل الأطفال الحقن (IPV)',
            'name_en': 'Inactivated Polio Vaccine',
            'desc': 'نسخة حقنية من لقاح الشلل تحتوي على فيروس ميت، تُعزز وتدعم المناعة المكتسبة ضد شلل الأطفال.'
        },
        'Penta': {
            'name_ar': 'اللقاح الخماسي (Pentavalent)',
            'name_en': 'Pentavalent Vaccine',
            'desc': 'لقاح مركب قوي مدمج يحمي من خمسة أمراض (الدفتيريا، الكزاز، السعال الديكي، الكبد ب، المستدمية النزلية ب).'
        },
        'Pneumo': {
            'name_ar': 'لقاح المكورات الرئوية (PCV)',
            'name_en': 'Pneumococcal Conjugate Vaccine',
            'desc': 'يحمي الرضع من بكتيريا المكورات المسببة لأغلب حالات الالتهاب الرئوي والتهاب الأذن والسحايا.'
        },
        'ROTA': {
            'name_ar': 'لقاح الروتا (Rota)',
            'name_en': 'Rotavirus Vaccine',
            'desc': 'قطرات فموية مهمة تحمي الأطفال من الإسهال الحاد والجفاف الخطير الناجم عن فيروس الروتا.'
        },
        'MR': {
            'name_ar': 'لقاح الحصبة والحصبة الألمانية (MR)',
            'name_en': 'Measles-Rubella Vaccine',
            'desc': 'يحمي الطفل من عدوى الحصبة سريعة الانتشار ومضاعفات الحصبة الألمانية التي تهدد صحته.'
        },
        'VitA': {
            'name_ar': 'فيتامين (أ) (Vit A)',
            'name_en': 'Vitamin A Supplementation',
            'desc': 'مكمل غذائي أساسي لتقوية المناعة العامة للطفل وتقليل أخطار العمى ومضاعفات الحصبة والإسهال.'
        },
        'TD': {
            'name_ar': 'اللقاح الثنائي (TD)',
            'name_en': 'Tetanus-Diphtheria Vaccine',
            'desc': 'جرعة تنشيطية تُعطى في سن دخول المدرسة لدعم واستمرار المناعة ضد أمراض الكزاز والدفتيريا.'
        },
    }

    v_objs = {}
    for key, data in vaccines_info.items():
        v, _ = Vaccine.objects.get_or_create(
            name_en=data['name_en'],
            defaults={
                'name_ar': data['name_ar'],
                'description': data['desc']
            }
        )
        v.name_ar = data['name_ar']
        v.description = data['desc']
        v.key = data['name_en']
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

    # ─── تنظيف السجلات المكررة أولاً (لو حصل Deploy متعدد سابقاً) ───────────────
    from django.db.models import Min
    # احتفظ فقط بأصغر id لكل مجموعة (vaccine + dose_number + stage) واحذف الباقي
    keep_ids = (
        VaccineSchedule.objects
        .values('vaccine_id', 'dose_number', 'stage')
        .annotate(min_id=Min('id'))
        .values_list('min_id', flat=True)
    )
    deleted_count, _ = VaccineSchedule.objects.exclude(id__in=keep_ids).delete()
    if deleted_count:
        print(f"  ✔ Cleaned up {deleted_count} duplicate vaccine schedule records.")

    # ─── إضافة الجداول بأمان (get_or_create يمنع التكرار) ────────────────────
    for v, dose, age, stage in schedules_data:
        VaccineSchedule.objects.get_or_create(
            vaccine=v,
            dose_number=dose,
            stage=stage,
            defaults={'age_in_months': age}
        )


    print("Successfully populated standard Yemen vaccines with Rich Data!")

if __name__ == '__main__':
    run()
