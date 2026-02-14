from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from medical.models import Child, Family, VaccineSchedule, VaccineRecord, ChildVaccineSchedule
from .models import Governorate, Directorate
from dateutil.relativedelta import relativedelta
from datetime import timedelta

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

        # 3. التحقق من الاكتمال (Auto-Archive Logic)
        remaining_vaccines = ChildVaccineSchedule.objects.filter(child=child, is_taken=False).count()
        if remaining_vaccines == 0:
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
    Premium Dashboard with Statistics and KPIs.
    """
    # 1. Total Children Count
    total_children = Child.objects.count()

    # 2. Today's Statistics
    today = timezone.now().date()
    today_records = VaccineRecord.objects.filter(date_given=today).count()

    # 3. Upcoming & Overdue
    next_week = today + timedelta(days=7)
    upcoming_appointments = ChildVaccineSchedule.objects.filter(
        due_date__range=[today, next_week],
        is_taken=False
    ).count()
    
    overdue_appointments = ChildVaccineSchedule.objects.filter(
        due_date__lt=today,
        is_taken=False
    ).count()
    
    # 4. Completion Rate
    completed_children = Child.objects.filter(is_completed=True).count()
    active_children = total_children - completed_children
    completion_rate = (completed_children / total_children * 100) if total_children > 0 else 0

    # 5. Chart Data: Last 7 Days Activity
    # Returns list of ints: [Day1, Day2, ..., Today]
    last_7_days = []
    days_labels = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        count = VaccineRecord.objects.filter(date_given=day).count()
        last_7_days.append(count)
        days_labels.append(day.strftime("%A")[:3]) # Short day name (e.g., Sat, Sun)

    # 6. Recent Activity
    recent_records = VaccineRecord.objects.select_related('child', 'vaccine', 'staff').order_by('-created_at')[:5]

    context = {
        'total_children': total_children,
        'today_records': today_records,
        'upcoming_appointments': upcoming_appointments,
        'overdue_appointments': overdue_appointments,
        'completion_rate': round(completion_rate, 1),
        'recent_records': recent_records,
        'chart_data': last_7_days,
        'chart_labels': days_labels,
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
    if request.method == 'POST':
        # 1. استلام البيانات
        child_name = request.POST.get('child_name')
        gender = request.POST.get('gender')
        dob_str = request.POST.get('dob') # Text 'YYYY-MM-DD'
        
        # تحويل النص إلى تاريخ لتجنب مشاكل الجمع لاحقاً
        from datetime import datetime
        try:
            dob_date = datetime.strptime(dob_str, '%Y-%m-%d').date()
            # Basic validation for year
            if dob_date.year > datetime.now().year + 1 or dob_date.year < 1900:
                 raise ValueError("Year out of range")
        except ValueError:
            messages.error(request, "تاريخ الميلاد غير صحيح. يرجى التأكد من كتابة السنة بشكل سليم (مثال: 2025).")
            return redirect('centers:add_child')

        father_name = request.POST.get('father_name')
        mother_name = request.POST.get('mother_name')
        
        gov_id = request.POST.get('governorate')
        dir_id = request.POST.get('directorate')

        # 2. منطق العائلة (Unified Family Logic)
        # البحث عن عائلة بنفس الأب والأم تماماً
        family = Family.objects.filter(father_name=father_name, mother_name=mother_name).first()
        
        is_new_account = False
        password = None
        
        if not family:
            is_new_account = True
            # إنشاء حساب جديد
            import random
            import string
            
            # Generate Access Code (F-YYYY-XXXX)
            # F = Family, YYYY = Birth Year of first child, XXXX = Random
            rand_suffix = random.randint(1000, 9999)
            username = f"F-{dob_date.year}-{rand_suffix}"
            password = username # كلمة المرور هي نفسها رقم الحساب للتسهيل
            
            # Create Django User
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user_account = User.objects.create_user(username=username, password=password, role='CUSTOMER')
            
            # Create Family
            family = Family.objects.create(
                father_name=father_name,
                mother_name=mother_name,
                account=user_account,
                access_code=username,
                created_by=request.user
            )

        # 3. إنشاء الطفل
        child = Child.objects.create(
            full_name=child_name,
            gender=gender,
            date_of_birth=dob_date, # Use the date object
            family=family,
            health_center=request.user.health_center, # Save the center!
            birth_governorate_id=gov_id,
            birth_directorate_id=dir_id,
            created_by=request.user
        )

        # 4. إنشاء "كرت التطعيم" (الجدول الزمني الشخصي)
        # ننسخ كل اللقاحات المطلوبة ونضع تواريخ استحقاقها بناء على ميلاد الطفل
        standard_schedules = VaccineSchedule.objects.all()
        personal_schedule_list = []
        
        for item in standard_schedules:
            # حساب تاريخ الاستحقاق مع دعم الكسور (مثل 1.5 شهر)
            import math
            months_int = int(item.age_in_months)
            days_extra = int((item.age_in_months - months_int) * 30)
            
            due_date = child.date_of_birth + relativedelta(months=months_int) + timedelta(days=days_extra)
            
            personal_schedule_list.append(
                ChildVaccineSchedule(
                    child=child,
                    vaccine_schedule=item,
                    due_date=due_date,
                    is_taken=False
                )
            )
        
        ChildVaccineSchedule.objects.bulk_create(personal_schedule_list)
        
        if is_new_account:
            msg = f"تم إنشاء حساب جديد بنجاح! 🎊\nرقم الحساب: {username}"
            messages.success(request, msg)
        else:
            messages.success(request, f"تم إضافة الطفل إلى حساب العائلة: {family.father_name} و {family.mother_name}")
            
        return redirect('centers:dashboard')

    # GET Request
    governorates = Governorate.objects.all()
    context = {
        'governorates': governorates
    }
    return render(request, 'centers/add_child.html', context)

def get_directorates(request):
    # API View Helper for AJAX dropdowns (Simple implementation for now)
    pass

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
