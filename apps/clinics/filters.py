from rest_framework.filters import BaseFilterBackend
from django.db.models import Q


class ServiceSearchFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        search = request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(code__icontains=search)
            )

        category = request.query_params.get('category', '').strip()
        if category:
            queryset = queryset.filter(category=category)

        is_active = request.query_params.get('isActive', '').strip().lower()
        if is_active == 'true':
            queryset = queryset.filter(is_active=True)
        elif is_active == 'false':
            queryset = queryset.filter(is_active=False)

        return queryset

    def get_schema_operation_parameters(self, view):
        return [
            {
                'name': 'search',
                'required': False,
                'in': 'query',
                'description': 'Search by service name or code',
                'schema': {'type': 'string'},
            },
            {
                'name': 'category',
                'required': False,
                'in': 'query',
                'description': 'Filter by category (consultation, laboratory, pharmacy, care)',
                'schema': {'type': 'string', 'enum': ['consultation', 'laboratory', 'pharmacy', 'care']},
            },
            {
                'name': 'isActive',
                'required': False,
                'in': 'query',
                'description': 'Filter by active status',
                'schema': {'type': 'string', 'enum': ['true', 'false']},
            },
        ]
