from django.urls import path

from .views import InvoiceListCreateView, InvoiceDetailView, InvoiceVoidView

urlpatterns = [
    path('', InvoiceListCreateView.as_view(), name='invoice-list-create'),
    path('<uuid:id>/', InvoiceDetailView.as_view(), name='invoice-detail'),
    path('<uuid:invoice_id>/void/', InvoiceVoidView.as_view(), name='invoice-void'),
]
