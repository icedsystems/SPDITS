from django.urls import path
from . import views

app_name = 'dashboards'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('admin/', views.AdminDashboardView.as_view(), name='admin'),
    path('partner/', views.PartnerDashboardView.as_view(), name='partner'),
    path('supervisor/', views.SupervisorDashboardView.as_view(), name='supervisor'),
    path('enumerator/', views.EnumeratorDashboardView.as_view(), name='enumerator'),
]
