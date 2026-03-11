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

    # Rich Data from Flutter App mapped to Backend Struct
    vaccines_info = {
        'BCG': {
            'name_ar': 'لقاح السل (BCG)',
            'name_en': 'Bacillus Calmette-Guérin',
            'desc': 'الوصف: لقاح حي مُخفَّف يحمي من مرض السل الرئوي، وهو أحد أخطر أمراض الجهاز التنفسي.\n'
                    'الوقاية: مرض السل (التدرن الرئوي) والتهاب السحايا السلي عند الأطفال.\n'
                    'الأعراض الجانبية المتوقعة: احمرار خفيف في مكان الحقنة، وقد تتكوّن بثرة صغيرة تزول بعد 2-3 أسابيع، بالإضافة لندبة صغيرة دائمة في الذراع — هذا طبيعي.'
        },
        'HepB': {
            'name_ar': 'لقاح الكبد البائي (Hep B)',
            'name_en': 'Hepatitis B Vaccine',
            'desc': 'الوصف: يحمي من فيروس التهاب الكبد B الذي يمكن أن يسبب التهاباً مزمناً في الكبد أو سرطانه.\n'
                    'الوقاية: التهاب الكبد الفيروسي B وما قد يترتب عليه من تليّف الكبد أو سرطانه.\n'
                    'الأعراض الجانبية المتوقعة: ألم خفيف أو احمرار في مكان الحقنة، ارتفاع طفيف في الحرارة (أقل من 38 درجة)، وتعب خفيف يزول خلال يوم أو يومين.'
        },
        'OPV': {
            'name_ar': 'لقاح شلل الأطفال الفموي (OPV)',
            'name_en': 'Oral Polio Vaccine',
            'desc': 'الوصف: قطرات تُعطى بالفم تحتوي على فيروس شلل الأطفال المُضعَّف، تبني مناعة قوية في الأمعاء.\n'
                    'الوقاية: مرض شلل الأطفال الذي يمكن أن يسبب الشلل الدائم أو الوفاة.\n'
                    'الأعراض الجانبية المتوقعة: قطرات بالفم — لا ألم من الحقن. نادراً جداً: إسهال خفيف.'
        },
        'IPV': {
            'name_ar': 'لقاح شلل الأطفال الحقن (IPV)',
            'name_en': 'Inactivated Polio Vaccine',
            'desc': 'الوصف: نسخة حقنية من لقاح الشلل تحتوي على فيروس ميت، تُعزز المناعة التي بدأها OPV.\n'
                    'الوقاية: شلل الأطفال (دعم إضافي للمناعة).\n'
                    'الأعراض الجانبية المتوقعة: ألم خفيف في مكان الحقنة، احمرار عابر، وحرارة خفيفة نادرة.'
        },
        'Penta': {
            'name_ar': 'اللقاح الخماسي (Pentavalent)',
            'name_en': 'Pentavalent Vaccine',
            'desc': 'الوصف: لقاح مركّب متعدد الفائدة يحمي من خمسة أمراض خطيرة في حقنة واحدة.\n'
                    'الوقاية: الدفتيريا، الكزاز، السعال الديكي، التهاب الكبد B، التهاب السحايا الهيموفيلي.\n'
                    'الأعراض الجانبية: ألم وتورم خفيف في فخذ الطفل (مكان الحقنة)، ارتفاع الحرارة حتى 38.5 درجة — يُعطى الباراسيتامول، بكاء الطفل لبضع ساعات — طبيعي.'
        },
        'Pneumo': {
            'name_ar': 'لقاح المكورات الرئوية (PCV)',
            'name_en': 'Pneumococcal Conjugate Vaccine',
            'desc': 'الوصف: يحمي من بكتيريا المكورات الرئوية التي هي من أكثر أسباب التهاب الرئة والتهاب السحايا عند الأطفال.\n'
                    'الوقاية: الالتهاب الرئوي، التهاب السحايا، التهاب الأذن الوسطى، تعفن الدم.\n'
                    'الأعراض الجانبية المتوقعة: ألم وتورم في مكان الحقنة، حرارة خفيفة مؤقتة، وخمول وقلة نشاط لمدة يوم أو يومين.'
        },
        'ROTA': {
            'name_ar': 'لقاح الروتا (Rota)',
            'name_en': 'Rotavirus Vaccine',
            'desc': 'الوصف: فيروس الروتا هو السبب الأول للإسهال الحاد عند الأطفال الصغار وقد يكون مميتاً بسبب الجفاف.\n'
                    'الوقاية: الإسهال الشديد والقيء الناجم عن فيروس الروتا.\n'
                    'الأعراض الجانبية: قطرات بالفم — لا ألم، إسهال خفيف أو قيء نادر.'
        },
        'MR': {
            'name_ar': 'لقاح الحصبة والحصبة الألمانية (MR)',
            'name_en': 'Measles-Rubella Vaccine',
            'desc': 'الوصف: يحمي من الحصبة المعدية جداً ومن الحصبة الألمانية التي تضر بشدة بالأجنة إذا أصابت الأم الحامل.\n'
                    'الوقاية: مرض الحصبة (أحد أكثر الأمراض المعدية في العالم) والحصبة الألمانية.\n'
                    'الأعراض الجانبية: احمرار في مكان الحقنة، طفح جلدي خفيف يشبه الحصبة بعد 7-12 يوم — طبيعي، ارتفاع طفيف في الحرارة لبضعة أيام.'
        },
        'VitA': {
            'name_ar': 'فيتامين (أ) (Vit A)',
            'name_en': 'Vitamin A Supplementation',
            'desc': 'الوصف: ليس لقاحاً بالمعنى الدقيق بل مكمل غذائي فاتح للمناعة، نقصه يسبب العمى الليلي وضعف المناعة.\n'
                    'الوقاية: العمى الناتج عن نقص فيتامين أ، ويقلل وفيات الأطفال من الحصبة والإسهال بنسبة 23-34٪.\n'
                    'الأعراض الجانبية المتوقعة: نادراً: صداع خفيف لبضع ساعات، غثيان خفيف أحياناً.'
        },
        'TD': {
            'name_ar': 'اللقاح الثنائي (TD)',
            'name_en': 'Tetanus-Diphtheria Vaccine',
            'desc': 'الوصف: يُعطى في سن المدرسة للتنشيط ضد الكزاز والدفتيريا اللذان لهما مضاعفات خطيرة جداً.\n'
                    'الوقاية: الكزاز (يسبب تشنجات وربما الوفاة) والدفتيريا (تسبب اختناقاً وقصور قلبي).\n'
                    'الأعراض الجانبية المتوقعة: ألم وتورم في الذراع لمدة 1-2 يوم، احمرار في مكان الحقنة، حرارة خفيفة نادرة.'
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

    print("Successfully populated standard Yemen vaccines with Rich Data!")

if __name__ == '__main__':
    run()
