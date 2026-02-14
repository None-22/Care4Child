from django.core.management.base import BaseCommand
from medical.models import Vaccine, VaccineSchedule

class Command(BaseCommand):
    help = 'Populates the database with standard vaccines and schedules'

    def handle(self, *args, **kwargs):
        # 1. تعريف اللقاحات
        # List: (name_ar, name_en, description)
        vaccines_data = [
            ("السل", "BCG", "يعطى عند الولادة - في الكتف الأيسر"),
            ("شلل الأطفال الفموي", "Oral Polio Vaccine (OPV)", "قطرتان في الفم"),
            ("الخماسي", "Pentavalent", "دفتيريا + تيتانوس + سعال ديكي + كبد ب + انفلونزا ب - حقن في الفخذ"),
            ("المكورات الرئوية", "Pneumococcal (PCV)", "حقن في الفخذ"),
            ("فيروس الروتا", "Rota Virus", "قطرات في الفم"),
            ("شلل الأطفال الحقن", "Inactivated Polio (IPV)", "حقن في الفخذ"),
            ("الحصبة والحصبة الألمانية", "Measles & Rubella (MR)", "حقن في الكتف"),
            ("فيتامين أ", "Vitamin A", "كبسولة بالفم"),
            ("الثلاثي البكتيري (منشطة)", "DPT", "دفتيريا + تيتانوس + سعال ديكي"),
            ("الكزاز (للأمهات)", "Tetanus (TT)", "للنساء في سن الإنجاب"),
        ]

        vaccine_objs = {}
        for name_ar, name_en, desc in vaccines_data:
            vac, created = Vaccine.objects.update_or_create(
                name_ar=name_ar,
                defaults={
                    'name_en': name_en,
                    'description': desc
                }
            )
            vaccine_objs[name_en] = vac # Use EN name as key for scheduling map below
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created Vaccine: {name_ar}'))
            else:
                self.stdout.write(f'Updated Vaccine: {name_ar}')

        # 2. تعريف الجدول الزمني (Standard Yemen EPI)
        # (Vaccine Key (EN), Dose Number, Age Months)
        schedule_data = [
            # At Birth (عند الولادة)
            ("BCG", 1, 0),
            ("Oral Polio Vaccine (OPV)", 0, 0), # Zero Dose

            # 1.5 Months (شعة ونصف - 6 أسابيع)
            ("Pentavalent", 1, 1), # Approx 1.5
            ("Oral Polio Vaccine (OPV)", 1, 1),
            ("Pneumococcal (PCV)", 1, 1),
            ("Rota Virus", 1, 1),

            # 2.5 Months (شهرين ونصف - 10 أسابيع)
            ("Pentavalent", 2, 2), # Approx 2.5
            ("Oral Polio Vaccine (OPV)", 2, 2),
            ("Pneumococcal (PCV)", 2, 2),
            ("Rota Virus", 2, 2),

            # 3.5 Months (3 شهور ونصف - 14 أسبوع)
            ("Pentavalent", 3, 3), # Approx 3.5
            ("Oral Polio Vaccine (OPV)", 3, 3),
            ("Pneumococcal (PCV)", 3, 3),
            ("Inactivated Polio (IPV)", 1, 3),

            # 9 Months (9 شهور)
            ("Measles & Rubella (MR)", 1, 9),
            ("Vitamin A", 1, 9),

            # 18 Months (سنة ونصف)
            ("Measles & Rubella (MR)", 2, 18),
            ("Vitamin A", 2, 18),
        ]

        # Clear old schedule to avoid duplicates/confusion if re-running heavily
        # VaccineSchedule.objects.all().delete() # Optional: destructive

        for vac_name_en, dose, age in schedule_data:
            if vac_name_en in vaccine_objs:
                vac = vaccine_objs[vac_name_en]
                sched, created = VaccineSchedule.objects.get_or_create(
                    vaccine=vac,
                    dose_number=dose,
                    defaults={'age_in_months': age}
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Scheduled {vac.name_ar} Dose {dose}'))
                else:
                    self.stdout.write(f'Schedule exists: {vac.name_ar} Dose {dose}')
    
        self.stdout.write(self.style.SUCCESS('Successfully populated vaccines with Bilingual Data!'))
