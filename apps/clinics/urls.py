from django.urls import path

from .views import ClinicDetailView, ServiceListCreateView, ServiceDetailView

urlpatterns = [
    path('', ClinicDetailView.as_view(), name='clinic-detail'),
    path('services/', ServiceListCreateView.as_view(), name='service-list-create'),
    path('services/<uuid:id>/', ServiceDetailView.as_view(), name='service-detail'),
]
