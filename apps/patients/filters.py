from django.db.models import Q
from rest_framework.filters import BaseFilterBackend


class PatientSearchFilter(BaseFilterBackend):
    """
    Searches across patient_id, name, and phone fields.
    A single `search` param handles all three.
    """

    def filter_queryset(self, request, queryset, view):
        search = request.query_params.get("search", "").strip()
        if not search:
            return queryset
        return queryset.filter(
            Q(name__icontains=search)
            | Q(phone__icontains=search)
            | Q(patient_id__icontains=search)
        )

    def get_schema_operation_parameters(self, view):
        return [
            {
                "name": "search",
                "required": False,
                "in": "query",
                "description": "Search by name, phone, or patient ID",
                "schema": {"type": "string"},
            }
        ]