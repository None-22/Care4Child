import os
import django

# تهيئة بيئة جانغو - تأكدي أن 'core' هو اسم مجلد الإعدادات
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from centers.models import Governorate, Directorate

def run():
    print("🚀 بدء استيراد المديريات (إب كاملة + أول 3 من البقية)...")
    
    # هيكل البيانات: "كود المحافظة": [ (كود المديرية، اسم عربي، اسم إنجليزي), ... ]
    data = {
        "01": [("01", "أزال", "Azal"), ("02", "التحرير", "At Tahrir"), ("03", "الثورة", "Ath Thawrah")],
        "02": [("01", "أرحب", "Arhab"), ("02", "الحصن", "Al Husn"), ("03", "الحيمة الخارجية", "Al Haymah Al Kharijiyah")],
        "03": [("01", "التواهي", "At Tawahi"), ("02", "المعلا", "Al Mualla"), ("03", "الشيخ عثمان", "Ash Shaikh Outhman")],
        "04": [("01", "المكلا", "Al Mukalla"), ("02", "الديس", "Ad Dis"), ("03", "الريدة وقصيعر", "Ar Raydah Wa Qusay-ar")],
        "05": [("01", "التعزية", "At Ta-iziyah"), ("02", "الشمايتين", "Ash Shamayatayn"), ("03", "الصلو", "As Silw")],
        "06": [("01", "التحيتا", "At Tuhayta"), ("02", "الجراحي", "Al Jarrahi"), ("03", "الحالي", "Al Hali")],
        # محافظة إب كاملة (20 مديرية)
        "07": [
            ("02", "الرضمة", "Ar Radmah"), ("03", "السبرة", "As Sabrah"),
            ("04", "السدة", "As Saddah"), ("05", "السياني", "As Sayyani"), ("06", "الشعر", "Ash Sha-ir"),
            ("07", "الظهار", "Ad Dhihar"), ("08", "العدين", "Al Udayn"), ("09", "القفر", "Al Qafr"),
            ("10", "المخادر", "Al Makhadir"), ("11", "المشنة", "Al Mashannah"), ("12", "النادرة", "An Nadirah"),
            ("13", "بعدان", "Ba-dan"), ("14", "جبلة", "Jiblah"), ("15", "حبيش", "Hubaysh"),
            ("16", "حزم العدين", "Hazm Al Udayn"), ("17", "ذي السفال", "Dhi As Sufal"),
            ("18", "فرع العدين", "Far Al Udayn"), ("19", "مذيخرة", "Mudhaykhirah"), ("20", "يريم", "Yarim")
        ],
        "08": [("01", "أحور", "Ahwar"), ("02", "المحفد", "Al Mahfad"), ("03", "الوضيع", "Al Wade-a")],
        "09": [("01", "البيضاء", "Al Bayda"), ("02", "الرياشة", "Ar Riyashiyyah"), ("03", "الزاهر", "Az Zahir")],
        "10": [("01", "الحد", "Al Had"), ("02", "الحوطة", "Al Hawtah"), ("03", "القبيطة", "Al Qubaytah")],
    }

    total_count = 0
    try:
        for gov_code, dirs in data.items():
            # البحث عن المحافظة باستخدام الكود الذي أدخلناه في السكربت السابق
            gov = Governorate.objects.filter(code=gov_code).first()
            
            if not gov:
                print(f"⚠️ تحذير: المحافظة ذات الكود {gov_code} غير موجودة، تخطي...")
                continue
            
            print(f"\n📂 معالجة مديريات {gov.name_ar}:")
            for d_code, d_ar, d_en in dirs:
                # إنشاء أو تحديث المديرية وربطها بالمحافظة
                # التعديل هنا: نستخدم المحافظة والكود كعوامل للبحث لضمان عدم حدوث خطأ التكرار (unique_together)
                obj, created = Directorate.objects.update_or_create(
                    governorate=gov,
                    code=d_code,
                    defaults={
                        'name_ar': d_ar,
                        'name_en': d_en,
                    }
                )
                status = "✅ إضافة" if created else "🔄 تحديث"
                print(f"   {status}: {d_ar}")
                total_count += 1

        print(f"\n✨ تمت المهمة بنجاح! تم استيراد {total_count} مديرية لـ 10 محافظات.")

    except Exception as e:
        print(f"❌ خطأ تقني: {e}")

if __name__ == '__main__':
    run()
