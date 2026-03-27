from django.db.models import Q
from rest_framework.filters import BaseFilterBackend


class PatientSearchFilter(BaseFilterBackend):
    """Search across patient_id, name, and phone. Also filter by gender."""

    def filter_queryset(self, request, queryset, view):
        search = request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(phone__icontains=search)
                | Q(patient_id__icontains=search)
            )

        gender = request.query_params.get('gender', '').strip()
        if gender:
            queryset = queryset.filter(gender=gender)

        return queryset

    def get_schema_operation_parameters(self, view):
        return [
            {
                'name': 'search',
                'required': False,
                'in': 'query',
                'description': 'Search by name, phone, or patient ID',
                'schema': {'type': 'string'},
            },
            {
                'name': 'gender',
                'required': False,
                'in': 'query',
                'description': 'Filter by gender (M, F, O)',
                'schema': {'type': 'string', 'enum': ['M', 'F', 'O']},
            },
        ]
