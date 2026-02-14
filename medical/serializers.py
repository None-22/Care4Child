from rest_framework import serializers
from .models import Vaccine, VaccineSchedule, Child, VaccineRecord

# 1. مترجم اللقاحات
class VaccineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vaccine
        fields = ['id', 'name_ar', 'name_en', 'description']

# 2. مترجم المواعيد
class VaccineScheduleSerializer(serializers.ModelSerializer):
    vaccine_name = serializers.CharField(source='vaccine.name_ar', read_only=True)
    
    class Meta:
        model = VaccineSchedule
        fields = ['id', 'vaccine', 'vaccine_name', 'dose_number', 'age_in_months', 'notes']

# 3. مترجم الطفل
class ChildSerializer(serializers.ModelSerializer):
    # نجلب اسم الأم (إذا وجد)
    mother_name = serializers.CharField(source='mother.username', read_only=True)

    class Meta:
        model = Child
        fields = '__all__' # كل الحقول (بما فيها رقم الجوال والاسم)

# 4. سجلات التطعيم
class VaccineRecordSerializer(serializers.ModelSerializer):
    vaccine_name = serializers.CharField(source='vaccine.name_ar', read_only=True)
    child_name = serializers.CharField(source='child.first_name', read_only=True)
    center_name = serializers.CharField(source='center.name', read_only=True)

    class Meta:
        model = VaccineRecord
        fields = ['id', 'child', 'child_name', 'vaccine', 'vaccine_name', 'dose_number', 'date_given', 'center', 'center_name', 'notes']