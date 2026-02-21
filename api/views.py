"""
ViewSets لـ Django REST API
"""
from rest_framework import viewsets, status, filters
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.exceptions import PermissionDenied
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from django_filters.rest_framework import DjangoFilterBackend

from django.shortcuts import render, get_object_or_404
import datetime
from datetime import timedelta     # For stats
from django.utils import timezone  # For stats

from users.models import CustomUser
from centers.models import HealthCenter, Governorate, Directorate
from medical.models import Child, Family, Vaccine, VaccineRecord, ChildVaccineSchedule

from .serializers import (
    GovernorateSerializer, DirectorateSerializer,
    HealthCenterListSerializer, HealthCenterDetailSerializer, HealthCenterCreateUpdateSerializer,
    UserListSerializer, UserDetailSerializer, UserCreateSerializer, UserUpdateSerializer,
    FamilyListSerializer, FamilyDetailSerializer, FamilyCreateUpdateSerializer,
    ChildListSerializer, ChildDetailSerializer, ChildCreateUpdateSerializer,
    VaccineListSerializer, VaccineDetailSerializer, VaccineCreateUpdateSerializer,
    VaccineRecordListSerializer, VaccineRecordDetailSerializer, VaccineRecordCreateUpdateSerializer
)
from .permissions import IsCenterStaffOrReadOnly


# ============== Governorate ViewSet ==============

class GovernorateViewSet(viewsets.ModelViewSet):
    """
    API للمحافظات (إدارة كاملة للسوبر أدمن)
    """
    queryset = Governorate.objects.all()
    serializer_class = GovernorateSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]


# ============== Directorate ViewSet ==============

class DirectorateViewSet(viewsets.ModelViewSet):
    """
    API للمديريات (إدارة كاملة للسوبر أدمن)
    """
    queryset = Directorate.objects.all()
    serializer_class = DirectorateSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['governorate']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
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
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
        
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['governorate', 'is_active']
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
        
        # 1. السوبر أدمن: يشوف الكل
        if user.is_superuser:
            return CustomUser.objects.all()
            
        # 2. مدير المركز: يشوف موظفي مركزه فقط
        if user.role == 'CENTER_MANAGER' and user.health_center:
            return CustomUser.objects.filter(health_center=user.health_center)
            
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
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """بيانات المستخدم الحالي"""
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data)

    def perform_create(self, serializer):
        # ميزة الأتمتة الذكية:
        # إذا كان المستخدم "مدير مركز"، نربط الموظف الجديد بمركزه تلقائياً ونعطيه صلاحية موظف
        if self.request.user.role == 'CENTER_MANAGER' and self.request.user.health_center:
            serializer.save(
                health_center=self.request.user.health_center,
                role='CENTER_STAFF',
                is_active=True
            )
        else:
            # في حال كان السوبر أدمن هو من يضيف، نترك له الحرية (أو نحفظ كما جاء)
            serializer.save()

# ============== Family ViewSet ==============

class FamilyViewSet(viewsets.ModelViewSet):
    """
    API للعائلات
    """
    queryset = Family.objects.all()
    # ... (rest of class config) ...
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # 1. الموظفين والإدارة: يرون كل العائلات (لأغراض البحث والتسجيل)
        if user.is_superuser or user.role in ['CENTER_MANAGER', 'CENTER_STAFF']:
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
    # الحماية: العائلات تقرأ فقط، الموظفين يقرأون ويكتبون
    permission_classes = [IsAuthenticated, IsCenterStaffOrReadOnly]
    
    def get_queryset(self):
        user = self.request.user
        
        # 1. السوبر أدمن ومدراء المراكز والموظفين: يرون كل الأطفال (لأغراض البحث والتطعيم)
        if user.is_superuser or user.role in ['CENTER_MANAGER', 'CENTER_STAFF']:
            return Child.objects.all()
            
        # 2. العائلات (Customer): يرون أطفالهم فقط
        return Child.objects.filter(family__account=user)
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['health_center', 'family', 'gender', 'is_completed']
    search_fields = ['full_name', 'family__father_name', 'family__mother_name']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ChildDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ChildCreateUpdateSerializer
        return ChildListSerializer
        
    def perform_create(self, serializer):
        # ميزة: ربط الطفل تلقائياً بمركز الموظف الذي أنشأه
        # ملاحظة: الصلاحيات تم التحقق منها عبر IsCenterStaffOrReadOnly
        serializer.save(
            health_center=self.request.user.health_center,
            created_by=self.request.user
        )

    # perform_update & perform_destroy removed (Handled by Permissions Class)
    
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
    
    def get_permissions(self):
        """
        الوصول:
        - قراءة (GET): مسموح لأي موظف مسجل دخول
        - تعديل (POST, PUT, DELETE): مسموح للسوبر أدمن فقط
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
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
    # الحماية: العوائل تقرأ فقط
    permission_classes = [IsAuthenticated, IsCenterStaffOrReadOnly]
    
    def get_queryset(self):
        user = self.request.user
        # 1. الموظفين: يرون كل السجلات (Unified Database)
        if user.is_superuser or user.role in ['CENTER_MANAGER', 'CENTER_STAFF']:
            return VaccineRecord.objects.all()
            
        # 2. العائلات: يرون سجلات أطفالهم فقط
        return VaccineRecord.objects.filter(child__family__account=user)

    def perform_create(self, serializer):
        # الصلاحيات تم التحقق منها عبر IsCenterStaffOrReadOnly
        serializer.save(staff=self.request.user)

    # perform_update & perform_destroy removed (Handled by Permissions Class)

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
        """إحصائيات التطعيمات"""
        total = VaccineRecord.objects.count()
        # إحصائيات بسيطة لأن الموديل الجديد لا يحتوي على حالة (status)
        today_count = VaccineRecord.objects.filter(date_given=datetime.date.today()).count()
        
        return Response({
            'total_vaccinations': total,
            'today_vaccinations': today_count,
        })


# ============== FCM Token Update View ==============
from rest_framework.views import APIView

class UpdateFCMTokenView(APIView):
    """
    API لتحديث رمز الإشعارات (Token) من تطبيق الجوال
    Endpoint: /api/update-fcm-token/
    Method: POST
    Body: { "token": "abc123..." }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get('token')
        if not token:
            return Response({'error': 'Token is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        user.fcm_token = token
        user.save()
        
        return Response({'message': 'FCM Token updated successfully', 'user': user.username})

class DashboardStatsView(APIView):
    """
    API لإرجاع إحصائيات الداشبورد (للمراكز والوزارة)
    Endpoint: /api/dashboard/stats/
    Method: GET
    Returns: JSON with KPIs and Charts Data
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # 1. تحديد النطاق (Filter Scope)
        start_date = timezone.now().date() - timedelta(days=30)
        
        # Base Querysets
        children_qs = Child.objects.all()
        records_qs = VaccineRecord.objects.all()
        
        # فلترة حسب صلاحية المستخدم
        if user.role in ['CENTER_MANAGER', 'HEALTH_STAFF'] and user.health_center:
            children_qs = children_qs.filter(health_center=user.health_center)
            records_qs = records_qs.filter(staff__health_center=user.health_center)
        
        # --- KPIs Calculation ---
        total_children = children_qs.count()
        completed_children = children_qs.filter(is_completed=True).count()
        
        # Dropout Rate (Logic: Missed > 7 days / Total Scheduled)
        # (Simplified for API speed: Children with missed vaccines / Total children)
        late_date = timezone.now().date() - timedelta(days=7)
        # This is expensive query, optimized for demonstration
        # In production, use a dedicated field or cache
        dropout_count = 0 # Placeholder for performance safety in API
        
        # Recent Activity (Last 5 records)
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
            
        # Upcoming Appointments (Next 2 days)
        tomorrow = timezone.now().date() + timedelta(days=1)
        # Note: We need to import ChildVaccineSchedule inside method or at top (checking if imported)
        from medical.models import ChildVaccineSchedule
        upcoming_qs = ChildVaccineSchedule.objects.filter(
            due_date__range=[timezone.now().date(), tomorrow],
            is_taken=False
        )
        if user.role in ['CENTER_MANAGER', 'HEALTH_STAFF'] and user.health_center:
            upcoming_qs = upcoming_qs.filter(child__health_center=user.health_center)
            
        upcoming_data = []
        for sched in upcoming_qs.select_related('child', 'vaccine_schedule__vaccine')[:5]:
            upcoming_data.append({
                'child_name': sched.child.full_name,
                'vaccine': sched.vaccine_schedule.vaccine.name_ar,
                'due_date': sched.due_date
            })

        data = {
            'kpis': {
                'total_children': total_children,
                'completed_children': completed_children,
                'completion_rate': round((completed_children / total_children * 100), 1) if total_children > 0 else 0,
            },
            'charts': {
                'vaccination_trend': [10, 15, 8, 20, 12, 18, 25], # Dummy data for Chart.js (Real logic needs aggregation)
                'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            },
            'recent_activity': activity_data,
            'upcoming_appointments': upcoming_data
        }
        
        return Response(data)

class ReportsByCenterView(APIView):
    """
    API تقرير أداء المراكز (للوحدة المركزية/الوزارة)
    Endpoint: /api/reports/by-center/
    Method: GET
    Returns: JSON list of centers with stats
    """
    permission_classes = [IsAdminUser] # للسوبر أدمن فقط

    def get(self, request):
        centers = HealthCenter.objects.filter(is_active=True).select_related('governorate', 'directorate')
        
        report_data = []
        for center in centers:
            # We can use annotation for better performance, but this is clearer for logic
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
            
        # Sort by rate descending (High to Low)
        report_data.sort(key=lambda x: x['coverage_rate'], reverse=True)
        
        return Response(report_data)
