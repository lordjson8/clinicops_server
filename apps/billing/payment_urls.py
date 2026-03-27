from django.urls import path

from .views import PaymentListCreateView, PaymentVoidView

urlpatterns = [
    path('', PaymentListCreateView.as_view(), name='payment-list-create'),
    path('<uuid:payment_id>/void/', PaymentVoidView.as_view(), name='payment-void'),
]
