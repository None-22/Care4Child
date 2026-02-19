"""
Serializers لـ Django REST API
"""
from rest_framework import serializers
import datetime
from .validators import validate_name, validate_phone_number, validate_past_date
from users.models import CustomUser
from centers.models import HealthCenter, Governorate, Directorate
from medical.models import Child, Family, Vaccine, VaccineRecord


# ============== Governorate & Directorate ==============

class GovernorateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Governorate
        fields = ['id', 'name_ar', 'name_en']


class DirectorateSerializer(serializers.ModelSerializer):
    governorate = GovernorateSerializer(read_only=True)
    
    class Meta:
        model = Directorate
        fields = ['id', 'name_ar', 'name_en', 'governorate']


# ============== Health Center ==============

class HealthCenterListSerializer(serializers.ModelSerializer):
    governorate_name = serializers.CharField(source='governorate.name_ar', read_only=True)
    directorate_name = serializers.CharField(source='directorate.name_ar', read_only=True)
    
    class Meta:
        model = HealthCenter
        fields = ['id', 'name_ar', 'name_en', 'center_code', 'governorate_name', 
                  'directorate_name', 'is_active', 'created_at']


class HealthCenterDetailSerializer(serializers.ModelSerializer):
    governorate = GovernorateSerializer(read_only=True)
    directorate = DirectorateSerializer(read_only=True)
    staff_count = serializers.SerializerMethodField()
    children_count = serializers.SerializerMethodField()
    
    class Meta:
        model = HealthCenter
        fields = ['id', 'name_ar', 'name_en', 'center_code', 'address', 'working_hours', 
                  'license_number', 'governorate', 
                  'directorate', 'is_active', 'staff_count', 'children_count', 
                  'created_at']
    
    def get_staff_count(self, obj):
        return CustomUser.objects.filter(health_center=obj).count()
    
    def get_children_count(self, obj):
        return Child.objects.filter(health_center=obj).count()


class HealthCenterCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthCenter
        fields = ['name_ar', 'name_en', 'address', 'working_hours', 
                  'license_number', 'governorate', 'directorate', 'is_active']


# ============== User ==============

class UserListSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    health_center_name = serializers.CharField(source='health_center.name_ar', read_only=True)
    
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'first_name', 'last_name', 'role', 
                  'role_display', 'health_center_name', 'is_active', 'date_joined']


class UserDetailSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    health_center = HealthCenterListSerializer(read_only=True)
    
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'first_name', 'last_name', 'phone', 
                  'role', 'role_display', 'health_center', 'is_active', 'date_joined', 
                  'last_login']


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'first_name', 'last_name', 'phone', 'password', 
                  'role', 'health_center', 'is_active']
        read_only_fields = ['role', 'health_center', 'is_active']
        extra_kwargs = {
            'first_name': {'validators': [validate_name]},
            'last_name': {'validators': [validate_name]},
            'phone': {'validators': [validate_phone_number]},
        }
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = CustomUser.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'phone', 'role', 'health_center', 'is_active']
        extra_kwargs = {
            'first_name': {'validators': [validate_name]},
            'last_name': {'validators': [validate_name]},
            'phone': {'validators': [validate_phone_number]},
        }


# ============== Family ==============

class FamilyListSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Family
        fields = ['id', 'father_name', 'mother_name', 'access_code', 'created_at']


class FamilyCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Family
        fields = ['father_name', 'mother_name', 'notes']
        extra_kwargs = {
            'father_name': {'validators': [validate_name]},
            'mother_name': {'validators': [validate_name]},
        }


# ============== Child List (Moved up for dependencies) ==============

class ChildListSerializer(serializers.ModelSerializer):
    health_center_name = serializers.CharField(source='health_center.name_ar', read_only=True)
    family_name = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    
    class Meta:
        model = Child
        fields = ['id', 'full_name', 'date_of_birth', 'age', 'gender', 
                  'health_center_name', 'family_name', 'is_completed', 'created_at']

    def get_family_name(self, obj):
        if obj.family:
            return f"{obj.family.father_name} & {obj.family.mother_name}"
        return "غير محدد"
    
    def get_age(self, obj):
        from datetime import date
        today = date.today()
        if not obj.date_of_birth: return 0
        age = today.year - obj.date_of_birth.year
        if (today.month, today.day) < (obj.date_of_birth.month, obj.date_of_birth.day):
            age -= 1
        return age


# ============== Vaccine ==============

class VaccineListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vaccine
        fields = ['id', 'name_ar', 'name_en', 'description']


class VaccineDetailSerializer(serializers.ModelSerializer):
    total_records = serializers.SerializerMethodField()
    
    class Meta:
        model = Vaccine
        fields = ['id', 'name_ar', 'name_en', 'description', 
                  'total_records']
    
    def get_total_records(self, obj):
        return VaccineRecord.objects.filter(vaccine=obj).count()


class VaccineCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vaccine
        fields = ['name_ar', 'name_en', 'description']


# ============== Vaccine Record ==============

class VaccineRecordListSerializer(serializers.ModelSerializer):
    child_name = serializers.CharField(source='child.full_name', read_only=True)
    vaccine_name = serializers.CharField(source='vaccine.name_ar', read_only=True)
    staff_name = serializers.CharField(source='staff.get_full_name', read_only=True)
    
    class Meta:
        model = VaccineRecord
        fields = ['id', 'child_name', 'vaccine_name', 'dose_number', 'staff_name', 
                  'date_given', 'created_at']


class VaccineRecordDetailSerializer(serializers.ModelSerializer):
    child = ChildListSerializer(read_only=True)
    vaccine = VaccineListSerializer(read_only=True)
    staff = UserListSerializer(read_only=True)
    
    class Meta:
        model = VaccineRecord
        fields = ['id', 'child', 'vaccine', 'dose_number', 'staff', 'date_given', 
                  'notes', 'created_at']


class VaccineRecordCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VaccineRecord
        fields = ['child', 'vaccine', 'dose_number', 'staff', 'date_given', 'notes']


# ============== Child Detail & Create ==============

class ChildDetailSerializer(serializers.ModelSerializer):
    health_center = HealthCenterListSerializer(read_only=True)
    # birth_health_center removed
    family = FamilyListSerializer(read_only=True)
    age = serializers.SerializerMethodField()
    vaccine_records = VaccineRecordListSerializer(source='vaccine_record_set', many=True, read_only=True)
    upcoming_vaccines = serializers.SerializerMethodField()
    stats = serializers.SerializerMethodField()
    
    class Meta:
        model = Child
        fields = ['id', 'full_name', 'date_of_birth', 'age', 'gender', 
                  'health_center', 'family',
                  'birth_governorate', 'birth_directorate', 'place_of_birth',
                  'is_completed', 'completed_date',
                  'vaccine_records', 'upcoming_vaccines', 'stats', 'created_at']
    
    def get_age(self, obj):
        from datetime import date
        today = date.today()
        if not obj.date_of_birth: return 0
        age = today.year - obj.date_of_birth.year
        if (today.month, today.day) < (obj.date_of_birth.month, obj.date_of_birth.day):
            age -= 1
        return age
    
    def get_upcoming_vaccines(self, obj):
        # جلب اللقاحات المستحقة وغير المأخوذة
        from medical.models import ChildVaccineSchedule
        schedules = ChildVaccineSchedule.objects.filter(child=obj, is_taken=False).order_by('due_date')
        
        # نحتاج لعمل سيريالايزر بسيط يدوياً أو استخدام واحد موجود
        # للتبسيط سنرجع البيانات كـ قائمة قواميس
        return [
            {
                'vaccine_name': s.vaccine_schedule.vaccine.name_ar,
                'dose_number': s.vaccine_schedule.dose_number,
                'due_date': s.due_date,
                'is_overdue': s.due_date < datetime.date.today()
            }
            for s in schedules
        ]

    def get_stats(self, obj):
        from medical.models import ChildVaccineSchedule
        total = ChildVaccineSchedule.objects.filter(child=obj).count()
        taken = VaccineRecord.objects.filter(child=obj).count()
        remaining = total - taken
        return {
            'total': total,
            'taken': taken,
            'remaining': remaining,
            'completion_percentage': int((taken / total) * 100) if total > 0 else 0
        }


class ChildCreateUpdateSerializer(serializers.ModelSerializer):
    # أضفنا هذه الحقول لاستقبال الأسماء من الفرونت إند
    father_name = serializers.CharField(write_only=True, validators=[validate_name])
    mother_name = serializers.CharField(write_only=True, validators=[validate_name])
    
    # حقول إضافية للموقع اليدوي (اختياري)
    governorate_text = serializers.CharField(write_only=True, required=False, allow_blank=True)
    directorate_text = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Child
        fields = [
            'full_name', 'date_of_birth', 'gender', 
            'father_name', 'mother_name', 
            'birth_governorate', 
            'birth_directorate', 'place_of_birth',
            'governorate_text', 'directorate_text'
        ]
        extra_kwargs = {
            'full_name': {'validators': [validate_name]},
            'date_of_birth': {'validators': [validate_past_date]},
        }

    def create(self, validated_data):
        # 1. استخراج البيانات الإضافية
        f_name = validated_data.pop('father_name')
        m_name = validated_data.pop('mother_name')
        
        gov_text = validated_data.pop('governorate_text', None)
        dir_text = validated_data.pop('directorate_text', None)
        
        # 2. منطق الموقع الهجين (Hybrid Location Logic)
        # إذا تم إرسال نصوص يدوية، ندمجها في place_of_birth ونتجاهل الـ IDs
        if gov_text and dir_text:
            current_place = validated_data.get('place_of_birth', '')
            validated_data['place_of_birth'] = f"{gov_text} - {dir_text} - {current_place}"
            validated_data['birth_governorate'] = None
            validated_data['birth_directorate'] = None

        # 3. نبحث عن العائلة أو ننشئها تلقائياً
        family_obj, created = Family.objects.get_or_create(
            father_name=f_name,
            mother_name=m_name
        )

        # 4. نحفظ الطفل
        child = Child.objects.create(family=family_obj, **validated_data)
        
        # ملاحظة: يتم إنشاء حساب المستخدم للعائلة تلقائياً عبر (Signals) في medical/signals.py
        # بمجرد إنشاء العائلة، يتم إنشاء User بنفس الكود.
        
        return child

    def to_representation(self, instance):
        """تضمين بيانات الأب والأم في الرد"""
        data = super().to_representation(instance)
        if instance.family:
            data['father_name'] = instance.family.father_name
            data['mother_name'] = instance.family.mother_name
            data['access_code'] = instance.family.access_code  # ✅ أهم حقل
        return data


class FamilyDetailSerializer(serializers.ModelSerializer):
    children_count = serializers.SerializerMethodField()
    children = ChildDetailSerializer(many=True, read_only=True)  # إضافة تفاصيل الأطفال
    
    class Meta:
        model = Family
        fields = ['id', 'father_name', 'mother_name', 'access_code', 'notes', 'children_count', 'children', 'created_at']
    
    def get_children_count(self, obj):
        return Child.objects.filter(family=obj).count()
