"""
URLs للـ API
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from .views import (
    GovernorateViewSet, DirectorateViewSet,
    HealthCenterViewSet, UserViewSet, FamilyViewSet,
    ChildViewSet, VaccineViewSet, VaccineRecordViewSet,
    UpdateFCMTokenView, DashboardStatsView, ReportsByCenterView,
    NotificationViewSet
)

# إنشاء Router
router = DefaultRouter()
router.register(r'governorates', GovernorateViewSet)
router.register(r'directorates', DirectorateViewSet)
router.register(r'health-centers', HealthCenterViewSet)
router.register(r'users', UserViewSet, basename='user')
router.register(r'families', FamilyViewSet)
router.register(r'children', ChildViewSet)
router.register(r'vaccines', VaccineViewSet)
router.register(r'vaccine-records', VaccineRecordViewSet)
router.register(r'notifications', NotificationViewSet, basename='notification')

app_name = 'api'

urlpatterns = [
    # Authentication
    path('auth/token/', obtain_auth_token, name='api_token_auth'),
    
    # API Routes
    path('', include(router.urls)),
    
    # Notification Token
    path('update-fcm-token/', UpdateFCMTokenView.as_view(), name='update_fcm_token'),
    
    # Dashboard Stats (New)
    path('dashboard/stats/', DashboardStatsView.as_view(), name='dashboard_stats'),
    # Reports (New)
    path('reports/by-center/', ReportsByCenterView.as_view(), name='reports_by_center'),
]
