from django.db.models import Q
from rest_framework.filters import BaseFilterBackend


class InvoiceFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        search = request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(invoice_number__icontains=search)
                | Q(patient__first_name__icontains=search)
                | Q(patient__last_name__icontains=search)
            )

        inv_status = request.query_params.get('status', '').strip()
        if inv_status:
            queryset = queryset.filter(status=inv_status)

        date_from = request.query_params.get('dateFrom', '').strip()
        if date_from:
            queryset = queryset.filter(issued_at__date__gte=date_from)

        date_to = request.query_params.get('dateTo', '').strip()
        if date_to:
            queryset = queryset.filter(issued_at__date__lte=date_to)

        patient_id = request.query_params.get('patientId', '').strip()
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)

        return queryset

    def get_schema_operation_parameters(self, view):
        return [
            {'name': 'search', 'required': False, 'in': 'query', 'description': 'Search by invoice number or patient name', 'schema': {'type': 'string'}},
            {'name': 'status', 'required': False, 'in': 'query', 'description': 'Filter by status', 'schema': {'type': 'string', 'enum': ['pending', 'partial', 'paid', 'cancelled']}},
            {'name': 'dateFrom', 'required': False, 'in': 'query', 'description': 'From date (YYYY-MM-DD)', 'schema': {'type': 'string', 'format': 'date'}},
            {'name': 'dateTo', 'required': False, 'in': 'query', 'description': 'To date (YYYY-MM-DD)', 'schema': {'type': 'string', 'format': 'date'}},
            {'name': 'patientId', 'required': False, 'in': 'query', 'description': 'Filter by patient UUID', 'schema': {'type': 'string', 'format': 'uuid'}},
        ]


class PaymentFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        search = request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(payment_id__icontains=search)
                | Q(invoice__invoice_number__icontains=search)
                | Q(invoice__patient__first_name__icontains=search)
                | Q(invoice__patient__last_name__icontains=search)
            )

        method = request.query_params.get('method', '').strip()
        if method:
            queryset = queryset.filter(payment_method=method)

        date_from = request.query_params.get('dateFrom', '').strip()
        if date_from:
            queryset = queryset.filter(payment_date__date__gte=date_from)

        date_to = request.query_params.get('dateTo', '').strip()
        if date_to:
            queryset = queryset.filter(payment_date__date__lte=date_to)

        return queryset

    def get_schema_operation_parameters(self, view):
        return [
            {'name': 'search', 'required': False, 'in': 'query', 'description': 'Search by payment ID, invoice, or patient', 'schema': {'type': 'string'}},
            {'name': 'method', 'required': False, 'in': 'query', 'description': 'Filter by payment method', 'schema': {'type': 'string', 'enum': ['cash', 'mtn_momo', 'orange_money', 'bank_transfer']}},
            {'name': 'dateFrom', 'required': False, 'in': 'query', 'description': 'From date (YYYY-MM-DD)', 'schema': {'type': 'string', 'format': 'date'}},
            {'name': 'dateTo', 'required': False, 'in': 'query', 'description': 'To date (YYYY-MM-DD)', 'schema': {'type': 'string', 'format': 'date'}},
        ]
