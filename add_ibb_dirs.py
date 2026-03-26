import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from centers.models import Governorate, Directorate

def run():
    print("Starting import...")
    try:
        # Get ibb governorate (assumes it has 'إب' in the name)
        ibb = Governorate.objects.filter(name_ar__contains='إب').first()
        if not ibb:
            # Maybe created with space or something else? Let's just create it if missing as a fallback, but user said they added it.
            ibb = Governorate.objects.create(name_ar="محافظة إب", code="14")
            print("Governorate Ibb wasn't found, so it was created.")
        else:
            print(f"Found Governorate: {ibb.name_ar} with code {ibb.code}")

        directorates_data = [
            ("1", "إب"),
            ("2", "الرضمة"),
            ("3", "السبرة"),
            ("4", "السدة"),
            ("5", "السياني"),
            ("6", "الشعر"),
            ("7", "الظهار"),
            ("8", "العدين"),
            ("9", "القفر"),
            ("10", "المخادر"),
            ("11", "المشنة"),
            ("12", "النادرة"),
            ("13", "بعدان"),
            ("14", "جبلة"),
            ("15", "حبيش"),
            ("16", "حزم العدين"),
            ("17", "ذي السفال"),
            ("18", "فرع العدين"),
            ("19", "مذيخرة"),
            ("20", "يريم"),
        ]

        count = 0
        for code, name in directorates_data:
            padded_code = code.zfill(2) # '01', '02', ..., '20'
            dir_name = f"مديرية {name}"
            d, created = Directorate.objects.get_or_create(
                governorate=ibb,
                name_ar=dir_name,
                defaults={'code': padded_code}
            )
            if not created and d.code != padded_code:
                d.code = padded_code
                d.save()
                
            count += 1
            print(f"Added: {dir_name} ({padded_code})")

        print(f"Successfully added {count} directorates to {ibb.name_ar}!")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    run()
