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
import json

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
    
      # --- 1. Top KPIs (أرقام سريعة للمدير) ---
    # 1.1 Defaulters (المتسربين): متأخرين أكثر من 3 أيام
    from django.db.models import Count, F, ExpressionWrapper, DateField
    from collections import defaultdict
    three_days_ago = today - timedelta(days=3)
    defaulters_count = ChildVaccineSchedule.objects.filter(
        child__health_center=center,
        is_taken=False,
        due_date__lte=three_days_ago
    ).count()

    # 1.2 Vaccinated Today (المطعمين اليوم)
    vaccinated_today = VaccineRecord.objects.filter(
        staff__health_center=center,
        date_given=today
    ).count()

    # 1.3 New Registered This Week (أطفال جدد هذا الأسبوع)
    seven_days_ago = today - timedelta(days=7)
    new_registered_week = Child.objects.filter(
        health_center=center,
        created_at__date__gte=seven_days_ago
    ).count()

    # --- 2. Weekly Visits Chart (مؤشر الزيارات الأسبوعي - Line Chart) ---
    # الزيارات الفعلية خلال آخر 7 أيام
    weekly_visits_labels = []
    weekly_visits_data = []
    for i in range(6, -1, -1):
        day_date = today - timedelta(days=i)
        # Arabic day name
        day_name = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"][day_date.weekday()]
        weekly_visits_labels.append(day_name)
        count = VaccineRecord.objects.filter(staff__health_center=center, date_given=day_date).count()
        weekly_visits_data.append(count)

    # --- 3. Upcoming Workload (مؤشر ضغط العمل المتوقع - Bar Chart) ---
    # الجرعات المستحقة خلال الـ 7 أيام القادمة بناءً على المواعيد
    upcoming_workload_labels = []
    upcoming_workload_data = []
    for i in range(1, 8): # من الغد حتى بعد أسبوع
        day_date = today + timedelta(days=i)
        day_name = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"][day_date.weekday()]
        upcoming_workload_labels.append(day_name)
        count = ChildVaccineSchedule.objects.filter(
            child__health_center=center,
            is_taken=False,
            due_date=day_date
        ).count()
        upcoming_workload_data.append(count)

    # --- 4. Community Reach (التقييم المجتمعي - Pie Chart/Table) ---
    # توزيع الأطفال النشطين حسب مديرية الميلاد (أو مكان الميلاد)
    community_reach_qs = Child.objects.filter(health_center=center).values(
        'birth_directorate__name_ar'
    ).annotate(count=Count('id')).order_by('-count')[:5]
    
    community_reach_labels = []
    community_reach_data = []
    for item in community_reach_qs:
        label = item['birth_directorate__name_ar'] if item['birth_directorate__name_ar'] else 'غير محدد'
        community_reach_labels.append(label)
        community_reach_data.append(item['count'])

    # --- 5. Recent Vaccination Activity (The "Live Feed") ---
    recent_records = VaccineRecord.objects.filter(
        staff__health_center=center
    ).select_related('child', 'vaccine').order_by('-date_given', '-id')[:5]

    # --- 6. Simplified Standard Stats ---
    total_children = Child.objects.filter(health_center=center).count()
    completed_children = Child.objects.filter(health_center=center, is_completed=True).count()
    
    # DEMO MODE LOGIC HAS BEEN COMPLETELY REMOVED

    context = {
        # 1. Top KPIs
        'defaulters_count': defaulters_count,
        'vaccinated_today': vaccinated_today,
        'new_registered_week': new_registered_week,
        
        # 2. Weekly Visits Chart (Line)
        'weekly_visits_labels': json.dumps(list(weekly_visits_labels)),
        'weekly_visits_data': json.dumps(list(weekly_visits_data)),
        
        # 3. Upcoming Workload (Bar)
        'upcoming_workload_labels': json.dumps(list(upcoming_workload_labels)),
        'upcoming_workload_data': json.dumps(list(upcoming_workload_data)),
        
        # 4. Community Reach (Pie/Table)
        'community_reach_labels': json.dumps(list(community_reach_labels)),
        'community_reach_data': json.dumps(list(community_reach_data)),
        
        # 5. Recent Activity
        'recent_records': recent_records,
        
        # 6. Generals
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
            try:
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
            except Exception as e:
                # في حال حدث خطأ تكرار (Constraint) أو غيره
                messages.error(request, "لم نتمكن من حفظ السجل. قد يكون هذا الطفل مسجلاً مسبقاً بنفس الاسم وتاريخ الميلاد.")
                return render(request, 'centers/add_child.html', {'governorates': Governorate.objects.all()})
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
        
        from django.db import IntegrityError
        
        try:
            if User.objects.filter(username__iexact=username).exists():
                messages.error(request, "اسم المستخدم هذا موجود مسبقاً، يرجى اختيار اسم آخر.")
                return render(request, 'centers/add_staff.html', {
                    'old_username': username,
                    'old_first': first_name,
                    'old_last': last_name,
                    'old_phone': phone,
                    'username_error': True
                })
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

        except IntegrityError:
            messages.error(request, "اسم المستخدم هذا موجود بالفعل، يرجى اختيار اسم آخر. (حدث تعارض)")
            return render(request, 'centers/add_staff.html', {
                'old_username': username,
                'old_first': first_name,
                'old_last': last_name,
                'old_phone': phone,
                'username_error': True
            })

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


