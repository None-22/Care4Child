from django.shortcuts import render, redirect, get_object_or_404
from .decorators import center_staff_required, center_manager_required
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from medical.models import Child, Family, VaccineSchedule, VaccineRecord, ChildVaccineSchedule
from .models import Governorate, Directorate, HealthCenter
from django.http import JsonResponse
from dateutil.relativedelta import relativedelta
from datetime import timedelta
from api.serializers import ChildCreateUpdateSerializer
from users.models import CustomUser

# ... (Previous views) ...

@login_required
def record_vaccine(request, child_id, schedule_id):
    schedule = get_object_or_404(VaccineSchedule, pk=schedule_id)
    child = get_object_or_404(Child, pk=child_id)
    
    # التحقق من عدم التكرار
    exists = VaccineRecord.objects.filter(
        child=child,
        vaccine=schedule.vaccine,
        dose_number=schedule.dose_number
    ).exists()
    
    if exists:
        messages.warning(request, "هذا اللقاح مسجل مسبقاً لهذا الطفل!")
    else:
        # 1. تسجيل الواقعة (أخذ اللقاح)
        VaccineRecord.objects.create(
            child=child,
            vaccine=schedule.vaccine,
            dose_number=schedule.dose_number,
            date_given=timezone.now().date(),
            staff=request.user
        )
        
        # 2. تحديث الكرت (الشطب على الموعد)
        from medical.models import ChildVaccineSchedule
        ChildVaccineSchedule.objects.filter(
            child=child, 
            vaccine_schedule=schedule
        ).update(is_taken=True)

        messages.success(request, f"تم تسجيل جرعة {schedule.vaccine.name_ar} بنجاح!")

        # 3. التحقق من الاكتمال (Auto-Archive Logic) - معدل
        # نتحقق فقط من اللقاحات "الأساسية"
        remaining_basic = ChildVaccineSchedule.objects.filter(
            child=child, 
            is_taken=False,
            vaccine_schedule__stage='BASIC' 
        ).count()
        if remaining_basic == 0:
            child.is_completed = True
            child.completed_date = timezone.now().date()
            child.save()
            messages.info(request, "🎉 مبروك! هذا الطفل استكمل جميع اللقاحات وتمت أرشفته.")
    
    return redirect('centers:child_detail', child_id=child.id)

@login_required
def child_detail_view(request, child_id):
    child = get_object_or_404(Child, pk=child_id)
    
    # 1. جلب الجدول الزمني
    schedules = VaccineSchedule.objects.select_related('vaccine').order_by('age_in_months', 'dose_number')
    
    # 2. جلب السجلات
    taken_records = VaccineRecord.objects.filter(child=child).select_related('vaccine')
    taken_map = {(rec.vaccine.id, rec.dose_number): rec for rec in taken_records}
    
    # 3. تجميع حسب العمر (الزيارة)
    # النتيجة: [ {'age': 0, 'label': 'عند الولادة', 'vaccines': [...]}, ... ]
    visits_map = {} # age -> {label, vaccines: []}
    
    for sched in schedules:
        age_key = sched.age_in_months
        if age_key not in visits_map:
            # تحديد العنوان
            if age_key == 0:
                label = "عند الولادة"
            elif age_key == 72:
                label = "سن دخول المدرسة (6 سنوات)"
            else:
                label = f"عمر {age_key} أشهر"
                
            visits_map[age_key] = {'age': age_key, 'label': label, 'vaccines': []}
        
        is_taken = (sched.vaccine.id, sched.dose_number) in taken_map
        record_info = taken_map.get((sched.vaccine.id, sched.dose_number))
        
        visits_map[age_key]['vaccines'].append({
            'schedule': sched,
            'is_taken': is_taken,
            'date_taken': record_info.date_given if record_info else None,
            'status': 'مكتمل' if is_taken else 'مستحق'
        })
    
    # تحويل القاموس لقائمة مرتبة
    visits_list = [visits_map[k] for k in sorted(visits_map.keys())]

    context = {
        'child': child,
        'visits': visits_list
    }
    return render(request, 'centers/child_detail.html', context)


@login_required
def dashboard_view(request):
    """
    Premium Dashboard with Engineering KPIs.
    "Smart Data" for "Smart Decisions".
    """
    user = request.user
    center = user.health_center
    today = timezone.now().date()
    
    # --- 1. Today's Efficiency (The Gauge) ---
    # Target: Scheduled appointments for THIS center today
    today_target = ChildVaccineSchedule.objects.filter(
        due_date=today, 
         # Only count children belonging to this center (Catchment Area)
        child__health_center=center
    ).count()
    
    # Actual: Vaccinations done BY this center's staff today (Unified DB Logic)
    # We count records created by staff generated from this center
    today_actual = VaccineRecord.objects.filter(
        date_given=today,
        staff__health_center=center
    ).count()
    
    efficiency_rate = int((today_actual / today_target * 100)) if today_target > 0 else 0

    # --- 2. Dropout Rate Funnel (The Funnel) ---
    # Metric: Compare total Dose 1 vs Dose 3 (Proxy for retention)
    # We look at records in the last 12 months for better relevance
    one_year_ago = today - timedelta(days=365)
    
    dose_1_count = VaccineRecord.objects.filter(
        staff__health_center=center,
        dose_number=1,
        date_given__gte=one_year_ago
    ).count()
    
    dose_3_count = VaccineRecord.objects.filter(
        staff__health_center=center,
        dose_number=3,
        date_given__gte=one_year_ago
    ).count()
    
    dropout_rate = 0
    if dose_1_count > 0:
        dropout_rate = round(((dose_1_count - dose_3_count) / dose_1_count * 100), 1)

    # --- 3. Weekly Peak Activity (Resource Management) ---
    # Aggregate by Day of Week (1=Sunday, 7=Saturday in Django usually, depends on DB)
    from django.db.models.functions import ExtractWeekDay
    from django.db.models import Count
    
    peak_data_qs = VaccineRecord.objects.filter(
        staff__health_center=center,
        date_given__gte=today - timedelta(days=30) # Last 30 days pattern
    ).annotate(weekday=ExtractWeekDay('date_given')).values('weekday').annotate(count=Count('id')).order_by('weekday')
    
    # Map Django weekday (1=Sunday..7=Saturday) to our list [Sun, Mon, ..., Sat]
    # Initialize 0 for all 7 days
    weekly_activity = [0] * 7 
    # Mappings might vary by DB, but typically 1=Sunday in Django
    for item in peak_data_qs:
        # Prevent index error if DB returns unexpected
        idx = (item['weekday'] - 1) % 7
        weekly_activity[idx] = item['count']
        
    weekly_labels = ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت']

    # --- 4. Age Distribution at Enrollment (Community Awareness) ---
    # Metric: When are they registering? (Birth vs Late)
    # We compare created_at with date_of_birth
    from django.db.models import F, ExpressionWrapper, DurationField
    
    # Calculate difference
    age_diff_qs = Child.objects.filter(health_center=center).annotate(
        enrollment_delay=ExpressionWrapper(F('created_at') - F('date_of_birth'), output_field=DurationField())
    )
    
    # Buckets
    age_dist = {
        'neonates': 0, # < 30 days (Ideal)
        'infants': 0,  # 1 month - 1 year
        'late': 0      # > 1 year
    }
    
    for child in age_diff_qs:
        days = child.enrollment_delay.days
        if days <= 30:
            age_dist['neonates'] += 1
        elif days <= 365:
            age_dist['infants'] += 1
        else:
            age_dist['late'] += 1
            
    age_labels = ['حديثي الولادة (< شهر)', 'رضّع (< سنة)', 'متأخرين (> سنة)']
    age_data = [age_dist['neonates'], age_dist['infants'], age_dist['late']]

    # --- 5. Vaccine Demand Forecasting (The Crystal Ball) ---
    # Metric: Expected doses next month (for Inventory)
    # We look at Month+1 from today
    next_month_start = today + timedelta(days=30)
    # Simple approx for next 30 days window
    next_month_end = next_month_start + timedelta(days=30)
    
    forecast_qs = ChildVaccineSchedule.objects.filter(
        child__health_center=center,
        due_date__range=[next_month_start, next_month_end],
        is_taken=False
    ).values('vaccine_schedule__vaccine__name_ar').annotate(count=Count('id')).order_by('-count')[:5]
    
    forecast_labels = [item['vaccine_schedule__vaccine__name_ar'] for item in forecast_qs]
    forecast_data = [item['count'] for item in forecast_qs]

    # --- 6. Zero-Dose Children (The "Invisible" Children) ---
    # Metric: Registered children who have received ZERO vaccines ever.
    # Critical for WHO/UNICEF reporting.
    zero_dose_count = Child.objects.filter(health_center=center, vaccine_records__isnull=True).count()

    # --- 7. Recent Vaccination Activity (The "Live Feed") ---
    # Replaced Staff Leaderboard with Actual child records as requested
    recent_records = VaccineRecord.objects.filter(
        staff__health_center=center
    ).select_related('child', 'vaccine').order_by('-date_given', '-id')[:5]

    # --- 8. Simplified Standard Stats ---
    total_children = Child.objects.filter(health_center=center).count()
    completed_children = Child.objects.filter(health_center=center, is_completed=True).count()
    
    # --- 9. DEMO MODE LOGIC (Enhanced) ---
    should_run_demo = (total_children == 0) or request.GET.get('demo')
    
    if should_run_demo:
        # Efficiency
        today_target = 40; today_actual = 35; efficiency_rate = 87
        # Dropout
        dose_1_count = 1200; dose_3_count = 1080; dropout_rate = 10.0
        # Peak
        weekly_activity = [45, 60, 55, 40, 30, 10, 5] 
        # Age Dist
        age_data = [300, 100, 50]
        # Forecast
        forecast_labels = ['شكل الأطفال', 'الخماسي', 'السداسي', 'الروتا', 'الحصبة']
        forecast_data = [150, 120, 110, 90, 85]
        # Zero-Dose
        zero_dose_count = 12
        # Recent Records Mock
        class MockObj:
            def __init__(self, **kwargs): self.__dict__.update(kwargs)
            
        recent_records = [
            MockObj(
                child=MockObj(full_name="أحمد محمد علي"),
                vaccine=MockObj(name_ar="الخماسي (1)"),
                dose_number=1,
                date_given=timezone.now().date()
            ),
             MockObj(
                child=MockObj(full_name="سارة خالد"),
                vaccine=MockObj(name_ar="شلل الأطفال"),
                dose_number=2,
                date_given=timezone.now().date()
            ),
             MockObj(
                child=MockObj(full_name="يوسف عمر"),
                vaccine=MockObj(name_ar="الحصبة"),
                dose_number=1,
                date_given=timezone.now().date() - timedelta(days=1)
            ),
        ]
        
        total_children = 450
        completed_children = 120

    context = {
        'is_demo_mode': should_run_demo,
        
        # 1. Efficiency Gauge
        'today_target': today_target,
        'today_actual': today_actual,
        'efficiency_rate': efficiency_rate,
        
        # 2. Dropout Funnel
        'dose_1_count': dose_1_count,
        'dose_3_count': dose_3_count,
        'dropout_rate': dropout_rate,
        
        # 3. Resource Mgmt (Heatmap)
        'weekly_activity': weekly_activity,
        'weekly_labels': weekly_labels,
        
        # 4. Age Distribution (Pie)
        'age_data': age_data,
        'age_labels': age_labels,
        
        # 5. Demand Forecast (Area Chart)
        'forecast_labels': forecast_labels,
        'forecast_data': forecast_data,
        
        # 6. Zero-Dose
        'zero_dose_count': zero_dose_count,
        
        # 7. Recent (Table)
        'recent_records': recent_records,
        
        # 8. Generals
        'total_children': total_children,
        'completed_children': completed_children,
    }
    return render(request, 'centers/dashboard.html', context)

@login_required
def registry_view(request):
    """
    Detached Vaccination Registry Page.
    """
    # 1. Fetch Vaccines and Schedules (Group by VACCINE)
    from medical.models import Vaccine
    vaccines = Vaccine.objects.prefetch_related('schedules').all()
    
    grouped_headers_list = []
    flat_header = []

    for vac in vaccines:
        doses = list(vac.schedules.all().order_by('dose_number'))
        if doses:
            grouped_headers_list.append({
                'label': vac.name_ar,
                'doses': doses
            })
            for i, sch in enumerate(doses):
                sch.is_group_end = (i == len(doses) - 1)
                flat_header.append(sch)
        
    # 2. Fetch Children (With Search)
    children = Child.objects.filter(is_completed=False).select_related('family').order_by('-created_at')

    query = request.GET.get('q')
    if query:
        from django.db.models import Q
        children = children.filter(
            Q(full_name__icontains=query) |
            Q(family__father_name__icontains=query) |
            Q(family__mother_name__icontains=query) |
            Q(family__access_code__icontains=query)
        )
    
    total_count = children.count()

    if not query:
        # Pagination could be added here
        children = children[:50] # Limit default view for performance

    # 3. Build Rows
    child_rows = []
    today = timezone.now().date()

    for child in children:
        records_map = {
            (rec.vaccine_id, rec.dose_number): rec 
            for rec in child.vaccine_records.all()
        }
        
        cells = []
        for col in flat_header:
            key = (col.vaccine.id, col.dose_number)
            is_taken = key in records_map
            
            status = 'future'
            date_val = None
            
            if is_taken:
                rec = records_map[key]
                status = 'taken'
                date_val = rec.date_given
            else:
                # Calculate Due Date
                if child.date_of_birth:
                    import math
                    months_int = int(col.age_in_months)
                    days_extra = int((col.age_in_months - months_int) * 30)
                    due_date = child.date_of_birth + relativedelta(months=months_int) + timedelta(days=days_extra)
                    date_val = due_date
                    
                    if today > due_date:
                        status = 'overdue'
                    elif today >= due_date - timedelta(days=14):
                         status = 'due'
                
            cells.append({
                'status': status,
                'date': date_val,
                'is_group_end': getattr(col, 'is_group_end', False)
            })

        child_rows.append({
            'child': child,
            'cells': cells
        })

    context = {
        'grouped_headers': grouped_headers_list,
        'flat_header': flat_header, 
        'child_rows': child_rows,
        'total_children_count': total_count,
        'search_query': query
    }
    return render(request, 'centers/registry.html', context)

@login_required
def add_child_view(request):
    """
    إضافة طفل جديد (النسخة الاحترافية باستخدام السيريالايزر)
    """
    if request.method == 'POST':
        # 1. نجهز البيانات (نسخة قابلة للتعديل)
        data = request.POST.copy()
        
        # 2. نربط أسماء الحقول في الـ HTML مع السيريالايزر
        data['full_name'] = request.POST.get('child_name') 
        data['date_of_birth'] = request.POST.get('dob')
        
        # ربط القوائم المنسدلة بأسماء الحقول في المودل
        data['birth_governorate'] = request.POST.get('governorate_select')
        data['birth_directorate'] = request.POST.get('directorate_select')
        
        # 3. نعطي البيانات للسيريالايزر وهو يتصرف (يفحص، ينشئ العائلة، يدمج النص)
        serializer = ChildCreateUpdateSerializer(data=data)
        
        if serializer.is_valid():
            # 4. الحفظ! (ونمرر له الموظف والمركز تلقائياً)
            child = serializer.save(
                created_by=request.user,
                health_center=request.user.health_center
            )
            
            # رسالة النجاح
            fam = child.family
            msg = f"تم تسجيل الطفل {child.full_name} بنجاح! ✅\nكود العائلة: {fam.access_code}"
            messages.success(request, msg)
            
            return redirect('centers:dashboard')
        else:
            # لو في أخطاء، نرجعها للمستخدم
            for field, errors in serializer.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            
            # نرجع لنفس الصفحة
            governorates = Governorate.objects.all()
            return render(request, 'centers/add_child.html', {'governorates': governorates})

    # GET Request
    governorates = Governorate.objects.all()
    return render(request, 'centers/add_child.html', {'governorates': governorates})

def get_locations_api(request):
    # API to fetch Directorates and Health Centers
    req_type = request.GET.get('type') # 'directorate' or 'center'
    parent_id = request.GET.get('parent_id')
    
    data = []
    
    if req_type == 'directorate' and parent_id:
        qs = Directorate.objects.filter(governorate_id=parent_id).values('id', 'name_ar')
        data = list(qs)
        
    elif req_type == 'center' and parent_id:
        # Note: Health Centers logic is preserved here if needed later
        qs = HealthCenter.objects.filter(directorate_id=parent_id).values('id', 'name_ar')
        data = list(qs)
        
    return JsonResponse({'data': data})

@login_required
def add_staff_view(request):
    # الحماية: التأكد أن المستخدم هو "مدير مركز"
    if not request.user.is_center_manager:
        messages.error(request, "عذراً، هذه الصفحة مخصصة لمدراء المراكز فقط.")
        return redirect('centers:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone = request.POST.get('phone')
        
        # التأكد من عدم وجود المستخدم
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        if User.objects.filter(username=username).exists():
            messages.error(request, "اسم المستخدم هذا موجود مسبقاً، يرجى اختيار اسم آخر.")
        else:
            # إنشاء الموظف
            staff_user = User.objects.create_user(
                username=username, 
                password=password, 
                role='CENTER_STAFF',
                first_name=first_name,
                last_name=last_name
            )
            # ربط الموظف بنفس مركز المدير
            staff_user.health_center = request.user.health_center
            staff_user.phone = phone
            staff_user.save()
            
            messages.success(request, f"تم إضافة الموظف {first_name} {last_name} بنجاح!")
            return redirect('centers:dashboard')

    return render(request, 'centers/add_staff.html')


@login_required
@center_manager_required
def staff_list_view(request):
    """عرض قائمة موظفي المركز للمدير فقط"""

    # جلب الموظفين التابعين لنفس المركز (باستثناء المدير نفسه)
    staff_members = CustomUser.objects.filter(
        health_center=request.user.health_center
    ).exclude(id=request.user.id).order_by('-date_joined')

    context = {
        'staff_members': staff_members
    }
    return render(request, 'centers/staff_list.html', context)


@login_required
@center_manager_required
def toggle_staff_status(request, staff_id):
    """تفعيل/إيقاف حساب موظف"""

    if request.method == 'POST':
        # التأكد أن الموظف يتبع نفس المركز
        # نستخدم get_user_model() لضمان التوافق
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        staff = get_object_or_404(User, id=staff_id, health_center=request.user.health_center)
        
        # عكس الحالة
        staff.is_active = not staff.is_active
        staff.save()
        
        action = "تفعيل" if staff.is_active else "إيقاف"
        if staff.is_active:
             messages.success(request, f"تم {action} حساب الموظف {staff.first_name} بنجاح.")
        else:
             messages.warning(request, f"تم {action} حساب الموظف {staff.first_name}. لن يتمكن من الدخول للنظام.")
        
    return redirect('centers:staff_list')


@login_required
@center_manager_required
def delete_staff(request, staff_id):
    """حذف حساب موظف نهائياً"""

    if request.method == 'POST':
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # التأكد أن الموظف يتبع نفس المركز
        staff = get_object_or_404(User, id=staff_id, health_center=request.user.health_center)
        
        staff_name = f"{staff.first_name} {staff.last_name}"
        staff.delete()
        
        messages.error(request, f"تم حذف الموظف {staff_name} نهائياً.")
        
    return redirect('centers:staff_list')


