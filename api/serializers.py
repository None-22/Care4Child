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
        fields = ['id', 'name_ar', 'name_en', 'code']


class DirectorateSerializer(serializers.ModelSerializer):
    governorate_details = GovernorateSerializer(source='governorate', read_only=True)
    
    class Meta:
        model = Directorate
        fields = ['id', 'name_ar', 'name_en', 'code', 'governorate', 'governorate_details']


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

    password = serializers.CharField(
        write_only=True, 
        min_length=8, 
        help_text="كلمة المرور الخاصة بحساب المركز (تستخدم لتسجيل الدخول)",
        required=False  # Not required strictly on updates
    )

    class Meta:
        model = HealthCenter
        fields = ['name_ar', 'name_en', 'address', 'working_hours', 
                  'license_number', 'governorate', 'directorate', 'is_active', 'password']
        validators = []  # نعطل validators الافتراضية ونستخدم validate() المخصص

    def validate(self, attrs):
        name_ar     = attrs.get('name_ar')
        governorate = attrs.get('governorate')
        directorate = attrs.get('directorate')

        if name_ar and governorate and directorate:
            qs = HealthCenter.objects.filter(
                name_ar=name_ar,
                governorate=governorate,
                directorate=directorate,
            )
            # عند التعديل نستثني المركز الحالي
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    'يوجد مركز بنفس الاسم في هذه المحافظة والمديرية بالفعل.'
                )
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        center = super().create(validated_data)
        
        # إنشاء حساب مدير المركز تلقائياً
        if password:
            from users.models import CustomUser
            username = center.name_ar.strip() if center.name_ar else f"HC_{center.id}"
            
            # التأكد من أن اليوزرنيم غير متكرر لمنع أخطاء الداتابيز
            if CustomUser.objects.filter(username=username).exists():
                username = f"{username}_{center.id}"
                
            CustomUser.objects.create_user(
                username=username,
                password=password,
                first_name="إدارة",
                last_name=center.name_ar,
                role='CENTER_MANAGER',
                health_center=center,
                is_active=True
            )
        return center

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        center = super().update(instance, validated_data)
        
        if password:
            from users.models import CustomUser
            manager = CustomUser.objects.filter(health_center=center, role='CENTER_MANAGER').first()
            if manager:
                manager.set_password(password)
                manager.save()
            else:
                username = center.name_ar.strip() if center.name_ar else f"HC_{center.id}"
                if CustomUser.objects.filter(username=username).exists():
                    username = f"{username}_{center.id}"
                    
                CustomUser.objects.create_user(
                    username=username,
                    password=password,
                    first_name="إدارة",
                    last_name=center.name_ar,
                    role='CENTER_MANAGER',
                    health_center=center,
                    is_active=True
                )
        return center


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
        # الحقول هنا للموظفين فقط، وسيتم تغييرها تماماً للعائلات عبر to_representation
        fields = ['id', 'username', 'first_name', 'last_name', 'role', 'role_display', 'health_center', 'is_active']

    def to_representation(self, instance):
        # 1. إذا كان المستخدم ولي أمر (عائلة)
        if instance.role == 'CUSTOMER':
            family = getattr(instance, 'family_profile', None)
            if family:
                return {
                    "id": instance.id,
                    "username": instance.username,  # هذا هو كود الدخول
                    "father_name": family.father_name,
                    "mother_name": family.mother_name,
                    "access_code": family.access_code,
                    "role_display": "ولي أمر",
                    "is_active": instance.is_active
                }
            # في حال لم يكن هناك عائلة مرتبطة
            return super().to_representation(instance)
        
        # 2. إذا كان موظفاً، نستخدم الرد الطبيعي الموضح في fields
        data = super().to_representation(instance)
        return data


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




class ProfileSelfUpdateSerializer(serializers.ModelSerializer):
    """سيريالايزر تعديل البروفايل الشخصي — الدور غير قابل للتعديل"""
    # username مخصص يقبل عربي ومسافات
    username = serializers.CharField(max_length=150, validators=[])
    new_password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    confirm_password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = CustomUser
        fields = ["username", "first_name", "last_name", "phone", "new_password", "confirm_password"]
        extra_kwargs = {
            "first_name": {"validators": [validate_name]},
            "last_name": {"validators": [validate_name]},
            "phone": {"validators": [validate_phone_number]},
        }

    def validate_username(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("اسم المستخدم لا يمكن أن يكون فارغاً.")
        qs = CustomUser.objects.filter(username=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("اسم المستخدم هذا مستخدم بالفعل.")
        return value

    def validate(self, attrs):
        p1 = attrs.get("new_password", "")
        p2 = attrs.get("confirm_password", "")
        if p1 or p2:
            if p1 != p2:
                raise serializers.ValidationError({"confirm_password": "كلمتا المرور غير متطابقتين."})
            from django.contrib.auth.password_validation import validate_password
            validate_password(p1, self.instance)
        return attrs

    def update(self, instance, validated_data):
        password = validated_data.pop("new_password", None)
        validated_data.pop("confirm_password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

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
    completion_percentage = serializers.SerializerMethodField()
    next_vaccine = serializers.SerializerMethodField()
    vaccine_records = serializers.SerializerMethodField()

    class Meta:
        model = Child
        fields = ['id', 'full_name', 'date_of_birth', 'age', 'gender',
                  'health_center_name', 'family_name', 'is_completed',
                  'completion_percentage', 'next_vaccine', 'vaccine_records', 'created_at']

    def get_vaccine_records(self, obj):
        """إرجاع سجلات التطعيم مع مفتاح جاهز يطابق col.id في JS مباشرةً"""
        records = obj.vaccine_records.select_related('vaccine').all()
        return [
            {
                'vaccine_name': r.vaccine.name_ar,
                # يستخدم حقل key من قاعدة البيانات، أو يرجع الاسم العربي كاحتياط
                'vaccine_key':  r.vaccine.key or r.vaccine.name_ar,
                'dose_number':  r.dose_number,
                'date_given':   str(r.date_given),
            }
            for r in records
        ]


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

    def get_completion_percentage(self, obj):
        # ✅ يقرأ مباشرةً من الحقل المحسوب سلفاً (annotate) — لا يستدعي قاعدة البيانات مجدداً
        taken = getattr(obj, 'taken_count', None)
        total = getattr(obj, 'total_schedules', None)
        if taken is None or total is None:
            # احتياطي: في حال استدعينا من مكان آخر بدون annotate
            from medical.models import ChildVaccineSchedule, VaccineRecord
            total = ChildVaccineSchedule.objects.filter(child=obj).count()
            taken = VaccineRecord.objects.filter(child=obj).count()
        return int((taken / total) * 100) if total > 0 else 0

    def get_next_vaccine(self, obj):
        from medical.models import ChildVaccineSchedule
        next_schedule = ChildVaccineSchedule.objects.filter(child=obj, is_taken=False).order_by('due_date').first()
        
        if next_schedule:
            import datetime
            return {
                'id': next_schedule.id,
                'vaccine_name': next_schedule.vaccine_schedule.vaccine.name_ar,
                'due_date': next_schedule.due_date,
                'is_overdue': next_schedule.due_date < datetime.date.today(),
            }
        return None


# ============== Vaccine ==============

class VaccineScheduleSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    dose_number = serializers.IntegerField()
    age_in_months = serializers.FloatField()


class VaccineListSerializer(serializers.ModelSerializer):
    schedules = serializers.SerializerMethodField()

    class Meta:
        model = Vaccine
        fields = ['id', 'name_ar', 'name_en', 'description', 'is_active', 'schedules']

    def get_schedules(self, obj):
        from medical.models import VaccineSchedule
        qs = VaccineSchedule.objects.filter(vaccine=obj).order_by('dose_number')
        return [{'id': s.id, 'dose_number': s.dose_number, 'age_in_months': s.age_in_months, 'stage': s.stage} for s in qs]


class VaccineDetailSerializer(serializers.ModelSerializer):
    total_records = serializers.SerializerMethodField()

    class Meta:
        model = Vaccine
        fields = ['id', 'name_ar', 'name_en', 'description', 'total_records']

    def get_total_records(self, obj):
        return VaccineRecord.objects.filter(vaccine=obj).count()


class VaccineCreateUpdateSerializer(serializers.ModelSerializer):
    schedules_data = serializers.ListField(
        child=serializers.DictField(), 
        write_only=True, 
        required=False,
        help_text="List of dicts: [{'dose_number': 1, 'age_in_months': 0}, ...]"
    )

    class Meta:
        model = Vaccine
        fields = ['id', 'name_ar', 'name_en', 'description', 'is_active', 'schedules_data']

    def _create_schedules(self, vaccine, schedules_data):
        from medical.models import VaccineSchedule
        for sched in schedules_data:
            age_in_months = float(sched.get('age_in_months', 0))
            stage = sched.get('stage')
            if not stage:
                stage = 'SCHOOL' if age_in_months >= 48 else 'BASIC'
            VaccineSchedule.objects.create(
                vaccine=vaccine,
                dose_number=int(sched.get('dose_number', 1)),
                age_in_months=age_in_months,
                stage=stage
            )

    def create(self, validated_data):
        schedules_data = validated_data.pop('schedules_data', [])
        vaccine = Vaccine.objects.create(**validated_data)
        self._create_schedules(vaccine, schedules_data)
        return vaccine

    def update(self, instance, validated_data):
        from medical.models import VaccineSchedule
        schedules_data = validated_data.pop('schedules_data', None)
        # Update vaccine fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        # If schedules_data was explicitly provided, replace all existing schedules
        if schedules_data is not None:
            instance.schedules.all().delete()
            self._create_schedules(instance, schedules_data)
        return instance


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
        read_only_fields = ['staff', 'date_given']


# ============== Child Detail & Create ==============

class ChildDetailSerializer(serializers.ModelSerializer):
    health_center = HealthCenterListSerializer(read_only=True)
    family = FamilyListSerializer(read_only=True)
    age = serializers.SerializerMethodField()
    vaccine_records = VaccineRecordListSerializer(source='vaccine_record_set', many=True, read_only=True)
    upcoming_vaccines = serializers.SerializerMethodField()
    full_vaccine_schedule = serializers.SerializerMethodField()
    stats = serializers.SerializerMethodField()
    birth_governorate_name = serializers.CharField(source='birth_governorate.name_ar', read_only=True, default='')
    birth_directorate_name = serializers.CharField(source='birth_directorate.name_ar', read_only=True, default='')
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True, default='النظام')

    class Meta:
        model = Child
        fields = ['id', 'full_name', 'date_of_birth', 'age', 'gender',
                  'health_center', 'family',
                  'birth_governorate', 'birth_governorate_name',
                  'birth_directorate', 'birth_directorate_name', 'place_of_birth',
                  'is_completed', 'completed_date',
                  'vaccine_records', 'upcoming_vaccines', 'full_vaccine_schedule', 'stats', 'created_at', 'created_by_name']
    
    def get_age(self, obj):
        from datetime import date
        today = date.today()
        if not obj.date_of_birth: return 0
        age = today.year - obj.date_of_birth.year
        if (today.month, today.day) < (obj.date_of_birth.month, obj.date_of_birth.day):
            age -= 1
        return age
    
    def get_upcoming_vaccines(self, obj):
        import datetime
        from medical.models import ChildVaccineSchedule
        schedules = ChildVaccineSchedule.objects.filter(child=obj, is_taken=False).order_by('due_date')
        
        return [
            {
                'id': s.id,
                'vaccine_name': s.vaccine_schedule.vaccine.name_ar,
                'dose_number': s.vaccine_schedule.dose_number,
                'due_date': s.due_date,
                'is_overdue': s.due_date < datetime.date.today(),
                'is_taken': s.is_taken
            }
            for s in schedules
        ]

    def get_full_vaccine_schedule(self, obj):
        import datetime
        from medical.models import ChildVaccineSchedule, VaccineRecord
        schedules = ChildVaccineSchedule.objects.filter(child=obj).select_related(
            'vaccine_schedule__vaccine'
        ).order_by('vaccine_schedule__age_in_months', 'vaccine_schedule__dose_number')

        vaccine_records = {
            (vr.vaccine_id, vr.dose_number): vr.date_given
            for vr in VaccineRecord.objects.filter(child=obj)
        }

        result = []
        for s in schedules:
            vs = s.vaccine_schedule
            vaccine_id = vs.vaccine_id
            dose_number = vs.dose_number
            date_given = vaccine_records.get((vaccine_id, dose_number))
            result.append({
                'schedule_id': vs.id,        # for the 'record vaccine' link
                'age_in_months': vs.age_in_months,
                'vaccine_name_ar': vs.vaccine.name_ar,
                'vaccine_name': vs.vaccine.name_ar,
                'dose_number': dose_number,
                'due_date': str(s.due_date) if s.due_date else None,
                'is_taken': s.is_taken,
                'is_overdue': not s.is_taken and s.due_date is not None and s.due_date < datetime.date.today(),
                'date_given': str(date_given) if date_given else None,
            })
        return result

    def get_stats(self, obj):
        # ✅ يقرأ مباشرةً من الحقل المحسوب سلفاً (annotate) — لا يستدعي قاعدة البيانات مجدداً
        taken = getattr(obj, 'taken_count', None)
        total = getattr(obj, 'total_schedules', None)
        if taken is None or total is None:
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
    country_text = serializers.CharField(write_only=True, required=False, allow_blank=True)
    governorate_text = serializers.CharField(write_only=True, required=False, allow_blank=True)
    directorate_text = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Child
        fields = [
            'full_name', 'date_of_birth', 'gender', 
            'father_name', 'mother_name', 
            'birth_governorate', 
            'birth_directorate', 'place_of_birth',
            'country_text', 'governorate_text', 'directorate_text'
        ]
        extra_kwargs = {
            'full_name': {'validators': [validate_name]},
            'date_of_birth': {'validators': [validate_past_date]},
        }

    def create(self, validated_data):
        # 0. Retrieve context from save() call
        center = validated_data.pop('health_center', None)
        created_by = validated_data.pop('created_by', None)

        # 1. استخراج البيانات الإضافية
        f_name = validated_data.pop('father_name')
        m_name = validated_data.pop('mother_name')
        
        country_text = validated_data.pop('country_text', None)
        gov_text = validated_data.pop('governorate_text', None)
        dir_text = validated_data.pop('directorate_text', None)
        
        # 2. منطق الموقع الهجين (Hybrid Location Logic)
        if gov_text and dir_text:
            current_place = validated_data.get('place_of_birth', '')
            parts = [p for p in [country_text, gov_text, dir_text, current_place] if p]
            validated_data['place_of_birth'] = ' - '.join(parts)
            validated_data['birth_governorate'] = None
            validated_data['birth_directorate'] = None

        # 3. نبحث عن العائلة أو ننشئها تلقائياً
        family_obj, created = Family.objects.get_or_create(
            father_name=f_name,
            mother_name=m_name
        )

        # ربط حساب العائلة بالمركز الصحي (إذا كان الحساب قد أنشئ للتو عبر Signals)
        # ننتظر قليلاً حتى ينتهي الـ signal من جلب الـ account
        if family_obj.account and not family_obj.account.health_center:
            family_obj.account.health_center = center
            family_obj.account.save()

        # 4. منع التكرار (Idempotency Check)
        child_name = validated_data.get('full_name')
        dob = validated_data.get('date_of_birth')
        existing_child = Child.objects.filter(
            family=family_obj,
            full_name=child_name,
            date_of_birth=dob
        ).first()

        if existing_child:
            return existing_child

        # 5. نحفظ الطفل ونربطه بمركز الموظف الحالي
        child = Child.objects.create(
            family=family_obj, 
            health_center=center,
            created_by=created_by,
            **validated_data
        )
        
        return child

    def to_representation(self, instance):
        """تضمين بيانات الأب والأم في الرد"""
        data = super().to_representation(instance)
        if instance.family:
            data['father_name'] = instance.family.father_name
            data['mother_name'] = instance.family.mother_name
            data['access_code'] = instance.family.access_code  # أهم حقل
        return data


class FamilyDetailSerializer(serializers.ModelSerializer):
    children_count = serializers.SerializerMethodField()
    children = ChildDetailSerializer(many=True, read_only=True)  # إضافة تفاصيل الأطفال
    
    class Meta:
        model = Family
        fields = ['id', 'father_name', 'mother_name', 'access_code', 'notes', 'children_count', 'children', 'created_at']
    
    def get_children_count(self, obj):
        return Child.objects.filter(family=obj).count()

# ============== Notifications ==============

from notifications.models import NotificationLog

class NotificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationLog
        fields = ['id', 'title', 'body', 'notification_type', 'is_read', 'created_at']
        read_only_fields = ['id', 'title', 'body', 'notification_type', 'created_at']