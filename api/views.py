"""
ViewSets لـ Django REST API
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.exceptions import PermissionDenied
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from django_filters.rest_framework import DjangoFilterBackend

from django.shortcuts import render, get_object_or_404
import datetime
from users.models import CustomUser
from centers.models import HealthCenter, Governorate, Directorate
from medical.models import Child, Family, Vaccine, VaccineRecord

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

class GovernorateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API للمحافظات
    """
    queryset = Governorate.objects.all()
    serializer_class = GovernorateSerializer
    permission_classes = [AllowAny]


# ============== Directorate ViewSet ==============

class DirectorateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API للمديريات
    """
    queryset = Directorate.objects.all()
    serializer_class = DirectorateSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['governorate']


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
