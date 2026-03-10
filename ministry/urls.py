from django.urls import path
from . import views

app_name = 'ministry'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('centers/', views.health_centers_view, name='health_centers'),
    path('governorates/', views.governorates_view, name='governorates'),
    path('vaccines/', views.vaccines_view, name='vaccines'),
    path('children/', views.children_view, name='children'),
    path('users/', views.users_view, name='users'),
    path('reports/', views.reports_view, name='reports'),
]
