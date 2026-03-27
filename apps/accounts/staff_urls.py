from django.urls import path

from .staff_views import (
    StaffListCreateView, StaffDetailView,
    StaffDeactivateView, StaffReactivateView,
)

urlpatterns = [
    path('', StaffListCreateView.as_view(), name='staff-list-create'),
    path('<uuid:staff_id>/', StaffDetailView.as_view(), name='staff-detail'),
    path('<uuid:staff_id>/deactivate/', StaffDeactivateView.as_view(), name='staff-deactivate'),
    path('<uuid:staff_id>/reactivate/', StaffReactivateView.as_view(), name='staff-reactivate'),
]
