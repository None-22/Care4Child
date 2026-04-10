"""
ViewSets لـ Django REST API
"""
from rest_framework import viewsets, status, filters, permissions
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.exceptions import PermissionDenied
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q  # ✅ للحسابات المُجمَّعة في قاعدة البيانات

from django.shortcuts import render, get_object_or_404
import datetime
from datetime import timedelta     # For stats
from django.utils import timezone  # For stats (هنا الاستدعاء الصحيح)

from users.models import CustomUser
from centers.models import HealthCenter, Governorate, Directorate
from medical.models import Child, Family, Vaccine, VaccineRecord, ChildVaccineSchedule

from .serializers import (
    GovernorateSerializer, DirectorateSerializer,
    HealthCenterListSerializer, HealthCenterDetailSerializer, HealthCenterCreateUpdateSerializer,
    UserListSerializer, UserDetailSerializer, UserCreateSerializer, UserUpdateSerializer,
    ProfileSelfUpdateSerializer,
    FamilyListSerializer, FamilyDetailSerializer, FamilyCreateUpdateSerializer,
    ChildListSerializer, ChildDetailSerializer, ChildCreateUpdateSerializer,
    VaccineListSerializer, VaccineDetailSerializer, VaccineCreateUpdateSerializer,
    VaccineRecordListSerializer, VaccineRecordDetailSerializer, VaccineRecordCreateUpdateSerializer,
    NotificationLogSerializer
)
from .permissions import IsCenterStaffOrReadOnly
from notifications.models import NotificationLog

# ============== Child Pagination ==============
class ChildPagination(PageNumberPagination):
    """
    Pagination class dedicated to ChildViewSet only.
    Returns 50 children per page.
    """
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


# ============== Governorate ViewSet ==============

class GovernorateViewSet(viewsets.ModelViewSet):
    """
    API للمحافظات (إدارة كاملة للسوبر أدمن والوزارة)
    """
    queryset = Governorate.objects.all()
    serializer_class = GovernorateSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            from api.permissions import IsAdminOrMinistry
            permission_classes = [IsAdminOrMinistry]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]


# ============== Directorate ViewSet ==============

class DirectorateViewSet(viewsets.ModelViewSet):
    """
    API للمديريات (إدارة كاملة للسوبر أدمن والوزارة)
    """
    queryset = Directorate.objects.all()
    serializer_class = DirectorateSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['governorate']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            from api.permissions import IsAdminOrMinistry
            permission_classes = [IsAdminOrMinistry]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]


# ============== Health Center ViewSet ==============

class HealthCenterViewSet(viewsets.ModelViewSet):
    """
    API للمراكز الصحية
    """
    queryset = HealthCenter.objects.all()
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            from api.permissions import IsAdminOrMinistry
            permission_classes = [IsAdminOrMinistry]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
        
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['governorate', 'directorate', 'is_active']
    search_fields = ['name_ar', 'name_en', 'center_code']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return HealthCenterDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return HealthCenterCreateUpdateSerializer
        return HealthCenterListSerializer
    
    @action(detail=True, methods=['get'])
    def staff(self, request, pk=None):
        """الموظفين في المركز"""
        center = self.get_object()
        staff = CustomUser.objects.filter(health_center=center)
        serializer = UserListSerializer(staff, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def children(self, request, pk=None):
        """الأطفال في المركز"""
        center = self.get_object()
        children = Child.objects.filter(health_center=center)
        serializer = ChildListSerializer(children, many=True)
        return Response(serializer.data)


# ============== User ViewSet ==============

class UserViewSet(viewsets.ModelViewSet):
    """
    API للمستخدمين
    """
    def get_queryset(self):
        user = self.request.user
        
        # 1. السوبر أدمن والوزارة: يشوف الكل
        if user.is_superuser or getattr(user, 'role', None) == 'MINISTRY':
            return CustomUser.objects.all()
            
        # 2. مدير المركز: يشوف موظفي مركزه فقط (باستثناء نفسه، فقط الموظفين)
        if getattr(user, 'role', None) == 'CENTER_MANAGER' and getattr(user, 'health_center', None):
            return CustomUser.objects.filter(health_center=user.health_center, role='CENTER_STAFF')
            
        # 3. الموظف العادي: لا يرى أي مستخدم (حتى نفسه في القائمة)
        # ملاحظة: بياناته الشخصية تأتي من الـ endpoint المخصص /me/
        return CustomUser.objects.none()
        
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['role', 'is_active', 'health_center']
    search_fields = ['username', 'first_name', 'last_name']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return UserDetailSerializer
        elif self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserListSerializer
    
    @action(detail=False, methods=['get', 'patch'])
    def me(self, request):
        """بيانات المستخدم الحالي / تعديل البروفايل الشخصي"""
        if request.method == 'GET':
            serializer = UserDetailSerializer(request.user)
            return Response(serializer.data)

        # PATCH — تعديل البروفايل
        serializer = ProfileSelfUpdateSerializer(
            request.user, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'تم تحديث البروفايل بنجاح.'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        # ميزة الأتمتة الذكية:
        if self.request.user.role == 'CENTER_MANAGER' and self.request.user.health_center:
            serializer.save(
                health_center=self.request.user.health_center,
                role='CENTER_STAFF',
                is_active=True
            )
        else:
            serializer.save()


# ============== Family ViewSet ==============

class FamilyViewSet(viewsets.ModelViewSet):
    """
    API للعائلات
    """
    queryset = Family.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # 1. الموظفين والإدارة: يرون كل العائلات (لأغراض البحث والتسجيل)
        if user.is_superuser or getattr(user, 'role', None) in ['CENTER_MANAGER', 'CENTER_STAFF', 'MINISTRY']:
            return Family.objects.all()
            
        # 2. العائلات (Customer): يرون بياناتهم فقط
        return Family.objects.filter(account=user)
        
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    filter_backends = [filters.SearchFilter]
    search_fields = ['father_name', 'mother_name', 'access_code']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return FamilyDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return FamilyCreateUpdateSerializer
        return FamilyListSerializer
    
    def perform_create(self, serializer):
        if self.request.user.role == 'CUSTOMER':
            raise PermissionDenied("عذراً، لا يمكن للعائلات إضافة أطفال. يرجى مراجعة المركز الصحي.")
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        if self.request.user.role == 'CUSTOMER':
            raise PermissionDenied("عذراً، لا يمكن للعائلات تعديل بيانات الأطفال.")
        serializer.save()

    def perform_destroy(self, instance):
        if self.request.user.role == 'CUSTOMER':
            raise PermissionDenied("عذراً، لا يمكن للعائلات حذف السجلات.")
        instance.delete()
    
    @action(detail=True, methods=['get'])
    def children(self, request, pk=None):
        """أطفال العائلة"""
        family = self.get_object()
        children = Child.objects.filter(family=family)
        serializer = ChildListSerializer(children, many=True)
        return Response(serializer.data)


# ============== Child ViewSet ==============

class ChildViewSet(viewsets.ModelViewSet):
    """
    API للأطفال
    """
    queryset = Child.objects.all()
    permission_classes = [IsAuthenticated, IsCenterStaffOrReadOnly]
    pagination_class = ChildPagination  # فقط هذا الـ ViewSet يستخدم Pagination
    
    def get_queryset(self):
        user = self.request.user

        # ✅ استخدام annotate() لحساب نسبة التحصين في استعلام واحد (يحل N+1 Query)
        base_qs = Child.objects.annotate(
            taken_count=Count('vaccine_records', distinct=True),
            total_schedules=Count('personal_schedule', distinct=True),
        ).select_related('family', 'health_center')

        if user.is_superuser or getattr(user, 'role', None) in ['CENTER_MANAGER', 'CENTER_STAFF', 'MINISTRY']:
            return base_qs
        return base_qs.filter(family__account=user)
        
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    
    # استخدام الملف api/filters.py للفلترات المتقدمة
    from .filters import ChildFilter
    filterset_class = ChildFilter
    
    search_fields = ['full_name', 'family__father_name', 'family__mother_name']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ChildDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ChildCreateUpdateSerializer
        return ChildListSerializer
        
    def perform_create(self, serializer):
        serializer.save(
            health_center=self.request.user.health_center,
            created_by=self.request.user
        )

    @action(detail=True, methods=['get'])
    def vaccine_records(self, request, pk=None):
        """سجلات التطعيمات للطفل"""
        child = self.get_object()
        records = VaccineRecord.objects.filter(child=child)
        serializer = VaccineRecordListSerializer(records, many=True)
        return Response(serializer.data)


# ============== Vaccine ViewSet ==============

class VaccineViewSet(viewsets.ModelViewSet):
    """
    API للقاحات
    """
    queryset = Vaccine.objects.all()
    
    def get_queryset(self):
        user = self.request.user
        qs = Vaccine.objects.all()
        # Ministry and admins see all vaccines including inactive ones
        is_ministry = getattr(user, 'role', None) == 'MINISTRY' or getattr(user, 'is_superuser', False)
        if not is_ministry:
            qs = qs.filter(is_active=True)
        # Allow filtering to only show vaccines that have a description (Rich Data)
        if self.request.query_params.get('has_description') == 'true':
            qs = qs.exclude(description__isnull=True).exclude(description__exact='')
        return qs
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            from api.permissions import IsAdminOrMinistry
            permission_classes = [IsAdminOrMinistry]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
        
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name_ar', 'name_en']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return VaccineDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return VaccineCreateUpdateSerializer
        return VaccineListSerializer


# ============== Vaccine Record ViewSet ==============

class VaccineRecordViewSet(viewsets.ModelViewSet):
    """
    API لسجلات التطعيمات
    """
    queryset = VaccineRecord.objects.all()
    permission_classes = [IsAuthenticated, IsCenterStaffOrReadOnly]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or getattr(user, 'role', None) in ['CENTER_MANAGER', 'CENTER_STAFF', 'MINISTRY']:
            return VaccineRecord.objects.all()
        return VaccineRecord.objects.filter(child__family__account=user)

    def perform_create(self, serializer):
        from django.utils import timezone
        serializer.save(staff=self.request.user, date_given=timezone.now().date())

    authentication_classes = [TokenAuthentication, SessionAuthentication]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['child', 'vaccine']
    search_fields = ['child__full_name', 'vaccine__name_ar']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return VaccineRecordDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return VaccineRecordCreateUpdateSerializer
        return VaccineRecordListSerializer
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        total = VaccineRecord.objects.count()
        today_count = VaccineRecord.objects.filter(date_given=datetime.date.today()).count()
        return Response({
            'total_vaccinations': total,
            'today_vaccinations': today_count,
        })


# ============== FCM Token Update View ==============

class UpdateFCMTokenView(APIView):
    """
    API لتحديث رمز الإشعارات
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get('fcm_token')
        if not token:
            return Response({'error': 'fcm_token is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        user.fcm_token = token
        user.save()
        return Response({'message': 'FCM Token updated successfully', 'user': user.username})


# ============== Dashboard Stats View ==============

class DashboardStatsView(APIView):
    """
    API لإرجاع إحصائيات الداشبورد (للمراكز والوزارة)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        today = timezone.now().date()
        
        children_qs = Child.objects.all()
        records_qs = VaccineRecord.objects.all()
        
        if user.role in ['CENTER_MANAGER', 'CENTER_STAFF'] and user.health_center:
            children_qs = children_qs.filter(health_center=user.health_center)
            records_qs = records_qs.filter(staff__health_center=user.health_center)
        
        # --- KPIs Calculation ---
        total_children = children_qs.count()
        completed_children = children_qs.filter(is_completed=True).count()
        
        # Calculate defaulters: children who are not completed AND have at least one past due schedule not taken
        defaulters_qs = ChildVaccineSchedule.objects.filter(
            child__in=children_qs.filter(is_completed=False),
            due_date__lt=today,
            is_taken=False
        ).values('child').distinct()
        dropout_count = defaulters_qs.count()
        
        vaccinated_today = records_qs.filter(date_given=today).count()
        
        recent_activity = records_qs.select_related('child', 'vaccine', 'staff').order_by('-date_given', '-id')[:5]
        activity_data = []
        for rec in recent_activity:
            activity_data.append({
                'id': rec.id,
                'child_name': rec.child.full_name,
                'vaccine': rec.vaccine.name_ar,
                'dose': rec.dose_number,
                'date': rec.date_given,
                'staff': rec.staff.username if rec.staff else 'System'
            })
            
        # المواعيد القادمة: من اليوم حتى 7 أيام قادمة فقط
        end_date = today + timedelta(days=7)
        upcoming_qs = ChildVaccineSchedule.objects.filter(
            due_date__range=[today, end_date],
            is_taken=False
        ).order_by('due_date')
        if user.role in ['CENTER_MANAGER', 'CENTER_STAFF'] and user.health_center:
            upcoming_qs = upcoming_qs.filter(child__health_center=user.health_center)

        # تجميع المواعيد حسب (الطفل + التاريخ)
        grouped = {}
        for sched in upcoming_qs.select_related('child', 'vaccine_schedule__vaccine'):
            key = (sched.child.id, str(sched.due_date))
            if key not in grouped:
                grouped[key] = {
                    'child_id': sched.child.id,
                    'child_name': sched.child.full_name,
                    'due_date': sched.due_date,
                    'age_in_months': sched.vaccine_schedule.age_in_months,  # القيمة الحقيقية (1.5، 2.5، ...)
                    'vaccines': []
                }
            v = sched.vaccine_schedule.vaccine
            grouped[key]['vaccines'].append({
                'schedule_id': sched.id,
                'vaccine_id': v.id,
                'name': v.name_ar,
                'dose_number': sched.vaccine_schedule.dose_number,
                'description': v.description or '',
            })

        upcoming_data = list(grouped.values())[:10]

        vaccine_dist_qs = records_qs.values('vaccine__name_ar').annotate(count=Count('id')).order_by('-count')[:12]
        vaccines_distribution = [{'name': v['vaccine__name_ar'], 'count': v['count']} for v in vaccine_dist_qs]

        centers_report = []
        if user.is_superuser or getattr(user, 'role', None) == 'MINISTRY':
            centers = HealthCenter.objects.filter(is_active=True)\
                .select_related('governorate', 'directorate')\
                .annotate(
                    total_children=Count('children', distinct=True),
                    completed_children=Count('children', filter=Q(children__is_completed=True), distinct=True),
                    defaulters_children=Count('children', filter=Q(
                        children__is_completed=False,
                        children__personal_schedule__due_date__lt=today, 
                        children__personal_schedule__is_taken=False
                    ), distinct=True)
                )
            for center in centers:
                ctotal = center.total_children
                ccompleted = center.completed_children
                cdefaulters = center.defaulters_children
                crate = round((ccompleted / ctotal * 100), 1) if ctotal > 0 else 0
                gov_name = center.governorate.name_ar if getattr(center, 'governorate', None) else 'غير محدد'
                dir_name = center.directorate.name_ar if getattr(center, 'directorate', None) else 'غير محدد'
                
                centers_report.append({
                    'id': center.id,
                    'name': center.name_ar,
                    'location': f"{gov_name} - {dir_name}",
                    'total_children': ctotal,
                    'completed_children': ccompleted,
                    'defaulters_children': cdefaulters,
                    'coverage_rate': crate,
                    'status': 'High' if crate > 80 else ('Medium' if crate > 50 else 'Low')
                })
            centers_report.sort(key=lambda x: x['coverage_rate'], reverse=True)

        last_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]
        chart_labels = [day.strftime('%a') for day in last_7_days] 
        
        vaccination_trend = []
        for day in last_7_days:
            count = records_qs.filter(date_given=day).count()
            vaccination_trend.append(count)

        data = {
            'kpis': {
                'total_children': total_children,
                'completed_children': completed_children,
                'completion_rate': round((completed_children / total_children * 100), 1) if total_children > 0 else 0,
                'defaulters_count': dropout_count,
                'vaccinated_today': vaccinated_today,
            },
            'charts': {
                'vaccination_trend': vaccination_trend, 
                'labels': chart_labels,
                'vaccines_distribution': vaccines_distribution
            },
            'recent_activity': activity_data,
            'upcoming_appointments': upcoming_data,
        }
        
        if user.is_superuser or getattr(user, 'role', None) == 'MINISTRY':
            data['centers_report'] = centers_report
            
        return Response(data)


# ============== Reports By Center View ==============

class ReportsByCenterView(APIView):
    """
    API تقرير أداء المراكز
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        centers = HealthCenter.objects.filter(is_active=True).select_related('governorate', 'directorate')
        
        report_data = []
        for center in centers:
            total = Child.objects.filter(health_center=center).count()
            completed = Child.objects.filter(health_center=center, is_completed=True).count()
            rate = round((completed / total * 100), 1) if total > 0 else 0
            
            report_data.append({
                'id': center.id,
                'name': center.name_ar,
                'location': f"{center.governorate.name_ar} - {center.directorate.name_ar}",
                'total_children': total,
                'completed_children': completed,
                'coverage_rate': rate,
                'status': 'High' if rate > 80 else ('Medium' if rate > 50 else 'Low')
            })
            
        report_data.sort(key=lambda x: x['coverage_rate'], reverse=True)
        return Response(report_data)


# ============== Vaccine Coverage Report View ==============

class AllVaccinesCoverageReportView(APIView):
    """
    API تقرير تغطية لكل اللقاحات مفلترة حسب المحافظة (ومديرية محددة اختيارياً)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        governorate_id = request.query_params.get('governorate_id')
        directorate_id = request.query_params.get('directorate_id')
        
        vaccines = Vaccine.objects.all()
        
        children_qs = Child.objects.all()
        records_qs = VaccineRecord.objects.all()
        
        if directorate_id:
            children_qs = children_qs.filter(health_center__directorate_id=directorate_id)
            records_qs = records_qs.filter(child__health_center__directorate_id=directorate_id)
        elif governorate_id:
            children_qs = children_qs.filter(health_center__governorate_id=governorate_id)
            records_qs = records_qs.filter(child__health_center__governorate_id=governorate_id)
            
        total_children = children_qs.count()
        
        # Group by vaccine and count distinct children
        coverage_data = records_qs.values('vaccine').annotate(
            vaccinated_count=Count('child', distinct=True)
        )
        
        counts_map = {item['vaccine']: item['vaccinated_count'] for item in coverage_data}
        
        result = []
        for v in vaccines:
            v_count = counts_map.get(v.id, 0)
            result.append({
                'vaccine_id': v.id,
                'vaccine_name': v.name_ar,
                'vaccinated_count': v_count,
                'total_children': total_children,
                'coverage_percentage': round((v_count / total_children * 100), 1) if total_children > 0 else 0
            })
            
        return Response({
            'filters': {
                'governorate_id': governorate_id,
                'directorate_id': directorate_id
            },
            'target_children': total_children,
            'vaccines_coverage': result
        })


# ================= Notifications =================

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API للإشعارات
    """
    serializer_class = NotificationLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return NotificationLog.objects.filter(recipient=self.request.user).order_by('-created_at')

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        notifications = self.get_queryset().filter(is_read=False)
        count = notifications.count()
        notifications.update(is_read=True)
        return Response({"message": f"{count} notifications marked as read.", "count": count})

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_one_read(self, request, pk=None):
        """تمييز إشعار واحد كمقروء"""
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response({"message": "Notification marked as read.", "id": notification.id})


# ================= Custom Auth Token =================

from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token

class CustomAuthTokenView(ObtainAuthToken):
    """
    تحقق من حالة المركز الصحي قبل إعطاء توكن للمستخدم.
    """
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        # تحقق مما إذا كان المستخدم موظفاً أو مديراً وينتمي إلى مركز غير نشط
        if hasattr(user, 'role') and user.role in ['CENTER_MANAGER', 'CENTER_STAFF']:
            if hasattr(user, 'health_center') and user.health_center:
                if not user.health_center.is_active:
                    if user.role == 'CENTER_STAFF':
                        error_msg = 'عذراً، المركز الصحي التابع لك موقوف حالياً، ولذلك تم إيقاف صلاحية دخولك للنظام كموظف.'
                    else:
                        error_msg = 'عذراً، هذا المركز الصحي موقوف حالياً. لا يمكنك تسجيل الدخول.'
                        
                    return Response({'error': error_msg}, status=status.HTTP_403_FORBIDDEN)
                
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk
        })


# ================= External Cron Webhook =================

from django.core.management import call_command

class TriggerRemindersCronView(APIView):
    """
    API لتشغيل إشعارات النظام من خلال خدمات مجانية مثل cron-job.org
    """
    permission_classes = [AllowAny]

    def get(self, request):
        secret = request.query_params.get('secret')
        # تحقق بسيط من المفتاح لضمان الأمان
        if secret != 'secure_care4child_cron_2026':
            raise PermissionDenied("Invalid Secret Key!")
            
        try:
            call_command('send_reminders')
            return Response({"success": True, "message": "Notification engine ran successfully."})
        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)