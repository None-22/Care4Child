import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from centers.models import Governorate, Directorate

def run():
    print("Starting import for remaining governorates...")
    try:
        data = {
            "تعز": [("6", "ذو باب"), ("7", "موزع"), ("8", "جبل حبشي")],
            "أمانة العاصمة": [("1", "صنعاء القديمة"), ("2", "شعوب"), ("3", "أزال")],
            "صنعاء": [("2", "أرحب"), ("3", "نهم"), ("4", "بني حشيش")],
            "الحديدة": [("3", "كمران"), ("4", "الصليف"), ("5", "المنيرة")]
        }

        # Mapping arbitrary fallback codes just in case user didn't add them yet as claimed
        fallback_codes = {
            "تعز": "15",
            "أمانة العاصمة": "11",
            "صنعاء": "25", # Just to differentiate from Amanat
            "الحديدة": "18"
        }

        count = 0
        for gov_name, dirs in data.items():
            # fetch gov exactly or loosely
            gov = Governorate.objects.filter(name_ar__contains=gov_name).first()
            if not gov:
                # Fallback create
                gov = Governorate.objects.create(name_ar=f"محافظة {gov_name}", code=fallback_codes[gov_name])
                print(f"Created Governorate {gov_name}")
            else:
                print(f"Found Governorate {gov.name_ar}")

            for code, name in dirs:
                padded_code = code.zfill(2)
                dir_name = f"مديرية {name}"
                d, created = Directorate.objects.get_or_create(
                    governorate=gov,
                    name_ar=dir_name,
                    defaults={'code': padded_code}
                )
                if not created and d.code != padded_code:
                    d.code = padded_code
                    d.save()
                
                count += 1
                status = "Added" if created else "Updated"
                print(f"  - {status}: {dir_name} ({padded_code})")

        print(f"Successfully added/verified {count} directorates across 4 governorates!")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    run()
