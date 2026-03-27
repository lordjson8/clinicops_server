from rest_framework.generics import GenericAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.core.mixins import ClinicScopedMixin
from apps.core.permissions import IsAnyClinicRole, IsOwnerOrAdmin, ReadAnyWriteRestricted

from .models import Service
from .serializers import ClinicSerializer, ServiceSerializer
from .filters import ServiceSearchFilter


# ──────────────────────────────────────────────
# Clinic settings
# ──────────────────────────────────────────────

class ClinicDetailView(GenericAPIView):
    """GET/PATCH the current user's clinic."""
    serializer_class = ClinicSerializer

    def get_permissions(self):
        if self.request.method in ('GET', 'HEAD', 'OPTIONS'):
            return [IsAnyClinicRole()]
        return [IsOwnerOrAdmin()]

    def get_object(self):
        return self.request.user.clinic

    @extend_schema(
        tags=['Clinics'],
        summary='Get clinic details',
        responses={200: ClinicSerializer},
    )
    def get(self, request):
        serializer = self.get_serializer(self.get_object())
        return Response(serializer.data)

    @extend_schema(
        tags=['Clinics'],
        summary='Update clinic settings',
        request=ClinicSerializer,
        responses={200: ClinicSerializer},
    )
    def patch(self, request):
        clinic = self.get_object()
        serializer = self.get_serializer(clinic, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# ──────────────────────────────────────────────
# Service CRUD (nested under clinic)
# ──────────────────────────────────────────────

class ServiceListCreateView(ClinicScopedMixin, ListCreateAPIView):
    """List / create services for the current clinic."""
    serializer_class = ServiceSerializer
    queryset = Service.objects.all()
    permission_classes = [ReadAnyWriteRestricted]
    filter_backends = [ServiceSearchFilter]

    @extend_schema(tags=['Services'], summary='List clinic services')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=['Services'], summary='Create a service')
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class ServiceDetailView(ClinicScopedMixin, RetrieveUpdateDestroyAPIView):
    """Retrieve / update / soft-delete a service."""
    serializer_class = ServiceSerializer
    queryset = Service.objects.all()
    lookup_field = 'id'

    def get_permissions(self):
        if self.request.method in ('GET', 'HEAD', 'OPTIONS'):
            return [IsAnyClinicRole()]
        return [IsOwnerOrAdmin()]

    def perform_destroy(self, instance):
        instance.soft_delete()

    @extend_schema(exclude=True)
    def put(self, request, *args, **kwargs):
        """Disabled — use PATCH for partial updates."""
        return super().put(request, *args, **kwargs)

    @extend_schema(tags=['Services'], summary='Get service details')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=['Services'], summary='Update a service')
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(tags=['Services'], summary='Delete (soft) a service')
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)
