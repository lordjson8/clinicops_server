from django.db.models import Q
from rest_framework.filters import BaseFilterBackend


class VisitFilter(BaseFilterBackend):
    """Filter visits by search, status, type, and date range."""

    def filter_queryset(self, request, queryset, view):
        search = request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(visit_id__icontains=search)
                | Q(patient__first_name__icontains=search)
                | Q(patient__last_name__icontains=search)
                | Q(patient__patient_id__icontains=search)
            )

        visit_status = request.query_params.get('status', '').strip()
        if visit_status:
            queryset = queryset.filter(status=visit_status)

        visit_type = request.query_params.get('type', '').strip()
        if visit_type:
            queryset = queryset.filter(visit_type=visit_type)

        date_from = request.query_params.get('dateFrom', '').strip()
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        date_to = request.query_params.get('dateTo', '').strip()
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        patient_id = request.query_params.get('patientId', '').strip()
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)

        return queryset

    def get_schema_operation_parameters(self, view):
        return [
            {
                'name': 'search',
                'required': False,
                'in': 'query',
                'description': 'Search by visit ID, patient name, or patient ID',
                'schema': {'type': 'string'},
            },
            {
                'name': 'status',
                'required': False,
                'in': 'query',
                'description': 'Filter by status',
                'schema': {'type': 'string', 'enum': ['open', 'invoiced', 'completed', 'cancelled']},
            },
            {
                'name': 'type',
                'required': False,
                'in': 'query',
                'description': 'Filter by visit type',
                'schema': {'type': 'string', 'enum': ['walkin', 'appointment', 'followup', 'emergency']},
            },
            {
                'name': 'dateFrom',
                'required': False,
                'in': 'query',
                'description': 'Filter visits from this date (YYYY-MM-DD)',
                'schema': {'type': 'string', 'format': 'date'},
            },
            {
                'name': 'dateTo',
                'required': False,
                'in': 'query',
                'description': 'Filter visits up to this date (YYYY-MM-DD)',
                'schema': {'type': 'string', 'format': 'date'},
            },
            {
                'name': 'patientId',
                'required': False,
                'in': 'query',
                'description': 'Filter visits for a specific patient (UUID)',
                'schema': {'type': 'string', 'format': 'uuid'},
            },
        ]
