"""
Data migration: يملأ حقل key للقاحات الموجودة في قاعدة البيانات
بناءً على القيم الموجودة سابقاً في VACCINE_KEY_MAP.
"""
from django.db import migrations

VACCINE_KEY_MAP = {
    'السل':                       'Bacillus Calmette-Guérin',
    'شلل الأطفال الفموي':         'Oral Polio Vaccine',
    'الخماسي':                    'Pentavalent Vaccine',
    'المكورات الرئوية':           'Pneumococcal Conjugate Vaccine',
    'فيروس الروتا':               'Rotavirus Vaccine',
    'شلل الأطفال الحقن':          'Inactivated Polio Vaccine',
    'الحصبة والحصبة الألمانية':   'Measles-Rubella Vaccine',
    'فيتامين أ':                  'Vitamin A Supplementation',
    'الثلاثي البكتيري (منشطة)':  'Tetanus-Diphtheria Vaccine',
}

def populate_vaccine_keys(apps, schema_editor):
    Vaccine = apps.get_model('medical', 'Vaccine')
    for name_ar, key in VACCINE_KEY_MAP.items():
        Vaccine.objects.filter(name_ar=name_ar, key__isnull=True).update(key=key)
        Vaccine.objects.filter(name_ar=name_ar, key='').update(key=key)


def reverse_vaccine_keys(apps, schema_editor):
    Vaccine = apps.get_model('medical', 'Vaccine')
    Vaccine.objects.filter(key__in=VACCINE_KEY_MAP.values()).update(key=None)


class Migration(migrations.Migration):

    dependencies = [
        ('medical', '0013_add_vaccine_key_field'),
    ]

    operations = [
        migrations.RunPython(populate_vaccine_keys, reverse_code=reverse_vaccine_keys),
    ]
