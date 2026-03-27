import os
import django

# تهيئة بيئة جانغو - تأكدي أن 'core' هو اسم مجلد الإعدادات عندك
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from centers.models import Governorate

def run():
    print("🚀 بدء استيراد المحافظات (أول 10 محافظات)...")
    
    # البيانات: (الكود، الاسم العربي بدون كلمة "محافظة"، الاسم الإنجليزي)
    governorates_data = [
        ("01", "أمانة العاصمة", "Amanat Al-Asimah"),
        ("02", "صنعاء", "Sana'a"),
        ("03", "عدن", "Aden"),
        ("04", "حضرموت", "Hadramaut"),
        ("05", "تعز", "Taiz"),
        ("06", "الحديدة", "Al-Hudaydah"),
        ("07", "إب", "Ibb"),
        ("08", "أبين", "Abyan"),
        ("09", "البيضاء", "Al-Bayda"),
        ("10", "لحج", "Lahj"),
    ]

    count = 0
    try:
        for code, name_ar, name_en in governorates_data:
            # استخدام update_or_create لضمان عدم التكرار وتحديث البيانات إذا وجدت
            gov, created = Governorate.objects.update_or_create(
                code=code,
                defaults={
                    'name_ar': name_ar,
                    'name_en': name_en,
                }
            )
            
            status = "✅ تم إضافة" if created else "🔄 تم تحديث"
            # الإخراج سيطبع الاسم الصافي بدون كلمة "محافظة"
            print(f"{status}: {name_ar} (الكود: {code})")
            count += 1

        print(f"\n✨ تمت العملية بنجاح! تم استيراد {count} محافظات.")

    except Exception as e:
        print(f"❌ حدث خطأ أثناء الاستيراد: {e}")

if __name__ == '__main__':
    run()
