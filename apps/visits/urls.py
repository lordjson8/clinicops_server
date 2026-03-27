from django.urls import path

from .views import (
    VisitListCreateView, VisitDetailView,
    VisitAddServiceView, VisitRemoveServiceView, VisitCancelView,
)

urlpatterns = [
    path('', VisitListCreateView.as_view(), name='visit-list-create'),
    path('<uuid:id>/', VisitDetailView.as_view(), name='visit-detail'),
    path('<uuid:visit_id>/services/', VisitAddServiceView.as_view(), name='visit-add-service'),
    path('<uuid:visit_id>/services/<uuid:service_id>/', VisitRemoveServiceView.as_view(), name='visit-remove-service'),
    path('<uuid:visit_id>/cancel/', VisitCancelView.as_view(), name='visit-cancel'),
]
