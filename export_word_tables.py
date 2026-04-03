import os
import django

# ربط السكربت بإعدادات المشروع
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.apps import apps
from django.db import models

# تصميم HTML: إنجليزي، حجم أصغر، ومرتب في المنتصف، وثلاثة حقول
html_content = """
<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="UTF-8">
    <title>Care4Child Data Dictionary</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f9f9f9; padding: 10px; font-size: 14px; }
        h1 { text-align: center; color: #1976D2; font-size: 22px; }
        h2 { color: #333; margin-top: 30px; margin-left: 10%; border-bottom: 2px solid #1976D2; padding-bottom: 3px; display: inline-block; font-size: 16px;}
        table { width: 80%; margin: 10px auto; border-collapse: collapse; background-color: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
        th { background-color: #1976D2; color: white; font-weight: bold; }
        tr:nth-child(even) { background-color: #f2f8fd; }
        tr:hover { background-color: #e6f2ff; }
        .app-name { color: gray; font-size: 0.8em; font-weight: normal; }
    </style>
</head>
<body>
    <h1>Care4Child Database Dictionary</h1>
"""

output_folder = 'schema_two'
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

my_apps = ['users', 'centers', 'medical', 'notifications', 'ministry']

print("جاري استخراج الجداول (مع تعديل الـ ForeignKey إلى id)...")

for app_name in my_apps:
    try:
        app_config = apps.get_app_config(app_name)
        for model in app_config.get_models():
            model_name = model.__name__
            
            html_content += f"<h2>Table: {model_name} <span class='app-name'>(App: {app_name})</span></h2>\n"
            html_content += "<table>\n"
            html_content += "<tr><th>Field Name</th><th>Data Type</th><th>Required</th></tr>\n"
            
            for field in model._meta.get_fields():
                if not isinstance(field, models.Field):
                    continue
                
                name = field.name
                field_type = field.get_internal_type()
                
                # --- التعديل هنا ليكون مطابق للصورة ---
                if field.is_relation and field.related_model:
                    field_type = f"{field_type} (id)"
                # --------------------------------------
                
                is_required = "No" if field.null else "Yes"
                
                html_content += f"<tr><td>{name}</td><td>{field_type}</td><td>{is_required}</td></tr>\n"
                
            html_content += "</table>\n"
            
    except LookupError:
        continue

html_content += """
</body>
</html>
"""

output_file = os.path.join(output_folder, 'Care4Child_Data_Dictionary.html')
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html_content)

print("-" * 30)
print(f"✅ تم بنجاح! افتح الملف الآن وبتلاقيه يكتب ForeignKey (id) زي ما طلبت.")