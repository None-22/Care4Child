from django.urls import path
from . import views

app_name = 'centers'

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('registry/', views.registry_view, name='registry'),
    path('add-child/', views.add_child_view, name='add_child'),
    path('child/<int:child_id>/', views.child_detail_view, name='child_detail'),
    path('vaccine/record/<int:child_id>/<int:schedule_id>/', views.record_vaccine, name='record_vaccine'),
    path('staff/add/', views.add_staff_view, name='add_staff'),
    path('api/locations/', views.get_locations_api, name='api_locations'),
]
