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
@center_staff_required
def record_vaccine(request, child_id, schedule_id):
    schedule = get_object_or_404(VaccineSchedule, pk=schedule_id)
    child = get_object_or_404(Child, pk=child_id)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    # التحقق من عدم التكرار
    exists = VaccineRecord.objects.filter(
        child=child,
        vaccine=schedule.vaccine,
        dose_number=schedule.dose_number
    ).exists()
    
    if exists:
        if is_ajax:
            return JsonResponse({'success': False, 'message': 'هذا اللقاح مسجل مسبقاً لهذا الطفل!'})
        messages.warning(request, "هذا اللقاح مسجل مسبقاً لهذا الطفل!")
    else:
        VaccineRecord.objects.create(
            child=child,
            vaccine=schedule.vaccine,
            dose_number=schedule.dose_number,
            date_given=timezone.now().date(),
            staff=request.user
        )
        
        from medical.models import ChildVaccineSchedule
        ChildVaccineSchedule.objects.filter(
            child=child, 
            vaccine_schedule=schedule
        ).update(is_taken=True)

        # التحقق من الاكتمال
        remaining_basic = ChildVaccineSchedule.objects.filter(
            child=child, 
            is_taken=False,
            vaccine_schedule__stage='BASIC' 
        ).count()
        if remaining_basic == 0:
            child.is_completed = True
            child.completed_date = timezone.now().date()
            child.save()

        if is_ajax:
            return JsonResponse({'success': True, 'date_given': str(timezone.now().date())})
        messages.success(request, f"تم تسجيل جرعة {schedule.vaccine.name_ar} بنجاح!")
    
    return redirect('centers:child_detail', child_id=child.id)



@login_required
@center_staff_required
def dashboard_view(request):
    """
    Dashboard shell view. All data is fetched client-side from /api/dashboard/stats/
    """
    return render(request, 'centers/dashboard.html')


@login_required
@center_staff_required
def registry_view(request):
    """
    Registry shell view. Children and vaccine grid headers
    are fetched client-side from /api/children/ and /api/vaccines/
    """
    return render(request, 'centers/registry.html')


@login_required
def child_detail_view(request, child_id):
    """
    Child detail shell view. Passes only the child_id to the template.
    All detail data is fetched client-side from /api/children/<id>/
    """
    if not (request.user.is_superuser or request.user.role in ['CENTER_STAFF', 'CENTER_MANAGER', 'MINISTRY']):
        messages.error(request, "ليس لديك صلاحية للوصول.")
        return redirect('users:login')
        
    return render(request, 'centers/child_detail.html', {'child_id': child_id})


@login_required
@center_staff_required
def add_child_view(request):
    """
    Add Child - Form POST (unchanged). GET loads governorates from API.
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
                
                # أشعار لوزارة الصحة عند التسجيل من خارج المنظومة (غير متزامن)
                is_manual = not request.POST.get('governorate_select') and request.POST.get('governorate_text')
                if is_manual:
                    import threading
                    from users.models import CustomUser
                    from notifications.models import NotificationLog

                    center = child.health_center
                    center_gov = center.directorate.governorate.name_ar if center and center.directorate else "غير معروف"
                    center_dir = center.directorate.name_ar if center and center.directorate else "غير معروف"
                    center_name = center.name_ar if center else "غير معروف"
                    creator_name = request.user.get_full_name() or request.user.username
                    child_id = child.id
                    child_name = child.full_name
                    place = child.place_of_birth

                    def send_ministry_notifications():
                        ministry_users = CustomUser.objects.filter(role='MINISTRY', is_active=True)
                        body_html = f"""
                        <div class="small" data-child-id="{child_id}">
                          تم إضافة طفل من خارج النظام: 
                          <span class="fw-bold text-primary"><i class="fas fa-child ms-1"></i>{child_name}</span>
                          <br>
                          <span class="text-muted mt-1 d-block"><i class="fas fa-map-marker-alt ms-1"></i>محل ميلاده الأصلي: <span class="fw-bold text-dark">{place}</span></span>
                          <hr class="my-2">
                          <span class="d-block mb-1 text-muted"><i class="fas fa-hospital ms-1 text-primary"></i> مسجل في: <span class="fw-bold text-dark">{center_gov} - {center_dir} - {center_name}</span></span>
                          <span class="d-block text-muted"><i class="fas fa-user-edit ms-1 text-info"></i> بواسطة الموظف: <span class="fw-bold text-dark">{creator_name}</span></span>
                        </div>
                        """
                        logs = [
                            NotificationLog(
                                recipient=mu,
                                title="تنبيه: طفل مسجل من خارج المنظومة",
                                body=body_html,
                                notification_type='SYSTEM'
                            ) for mu in ministry_users
                        ]
                        NotificationLog.objects.bulk_create(logs)

                    threading.Thread(target=send_ministry_notifications, daemon=True).start()
                
                # رسالة النجاح — الكود في سطر منفصل لسهولة النسخ
                fam = child.family
                messages.success(request, f"تم تسجيل الطفل {child.full_name} بنجاح!\nكود دخول العائلة للتطبيق:\n{fam.access_code}")
                
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

    # GET Request — governorates are now loaded client-side via /api/governorates/
    return render(request, 'centers/add_child.html')

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
@center_manager_required
def add_staff_view(request):
    # الحماية: التأكد أن المستخدم هو "مدير مركز"
    if not request.user.is_center_manager:
        messages.error(request, "عذراً، هذه الصفحة مخصصة لمدراء المراكز فقط.")
        return redirect('centers:dashboard')

    if request.method == 'POST':
        import unicodedata
        # تطبيع Unicode (NFKC) على اليوزرنيم لضمان التطابق عند تسجيل الدخول لاحقاً
        # هذا يعالج الحروف العربية التي قد تأتي بأشكال Unicode مختلفة
        raw_username = request.POST.get('username', '')
        username = unicodedata.normalize('NFKC', raw_username).strip()
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone = request.POST.get('phone')
        
        # التأكد من عدم وجود المستخدم أو محاولة النقل (Transfer Logic)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        from django.db import IntegrityError
        
        try:
            existing_user = User.objects.filter(username__iexact=username).first()
            if existing_user:
                # التحقق إذا كانت كلمة المرور صحيحة للقيام بعملية النقل التلقائي
                if existing_user.check_password(password):
                    if existing_user.role in ['ADMIN', 'MINISTRY']:
                        messages.error(request, "لا يمكن نقل حسابات الإدارة العليا لمركزك. يرجى استخدام اسم مستخدم آخر.")
                        return render(request, 'centers/add_staff.html', {
                            'old_username': username, 'old_first': first_name,
                            'old_last': last_name, 'old_phone': phone, 'username_error': True
                        })
                    else:
                        # التأكد من إخلاء الطرف (أن الموظف ليس نشطاً في مركز آخر)
                        if existing_user.is_active and existing_user.health_center != request.user.health_center:
                            messages.error(request, f"هذا الموظف لا يزال مسجلاً كـ (نشط) في مركز آخر ({existing_user.health_center.name_ar if existing_user.health_center else 'غير محدد'}). يجب إيقاف حسابه في المركز القديم أولاً (إخلاء طرف) لتتمكن من سحبه.")
                            return render(request, 'centers/add_staff.html', {
                                'old_username': username, 'old_first': first_name,
                                'old_last': last_name, 'old_phone': phone, 'username_error': True
                            })
                            
                        # التأكد إذا كان مسجلاً ونشطاً في نفس المركز
                        if existing_user.is_active and existing_user.health_center == request.user.health_center:
                            messages.warning(request, "هذا الموظف مسجل ونشط بالفعل في مركزك!")
                            return redirect('centers:dashboard')

                        # عملية نقل الموظف (Re-assignment) أو إعادة تفعيله
                        existing_user.health_center = request.user.health_center
                        existing_user.is_active = True
                        existing_user.first_name = first_name
                        existing_user.last_name = last_name
                        existing_user.phone = phone
                        existing_user.role = 'CENTER_STAFF'
                        existing_user.save()
                        
                        messages.success(request, f"حساب الموظف ({username}) كان موجوداً مسبقاً، تمت مصادقته ونقله لمركزك بنجاح!")
                        return redirect('centers:dashboard')
                else:
                    messages.error(request, "اسم المستخدم موجود مسبقاً! إذا كان الموظف لديه حساب قديم وتريد ضمه لمركزك، يرجى إدخال كلمة مروره القديمة الصحيحة. أو اختر اسم مستخدم جديد.")
                    return render(request, 'centers/add_staff.html', {
                        'old_username': username,
                        'old_first': first_name,
                        'old_last': last_name,
                        'old_phone': phone,
                        'username_error': True
                    })
            else:
                # إنشاء الموظف الجديد
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
            messages.error(request, "حدث تعارض أثناء إنشاء الحساب، يرجى المحاولة باسم مختلف.")
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
    """Staff list shell view. Data fetched client-side from /api/users/"""
    return render(request, 'centers/staff_list.html')



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