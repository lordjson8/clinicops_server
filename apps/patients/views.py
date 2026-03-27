from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.core.mixins import ClinicScopedMixin
from apps.core.permissions import IsAnyClinicRole, IsOwnerAdminOrReceptionist, ReadAnyWriteRestricted

from .models import Patient
from .serializers import PatientListSerializer, PatientDetailSerializer
from .filters import PatientSearchFilter


class PatientListCreateView(ClinicScopedMixin, ListCreateAPIView):
    queryset = Patient.objects.all()
    permission_classes = [ReadAnyWriteRestricted]
    write_roles = ('owner', 'admin', 'receptionist')
    filter_backends = [PatientSearchFilter]

    def get_serializer_class(self):
        return PatientListSerializer if self.request.method == 'GET' else PatientDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            clinic=self.request.user.clinic,
            registered_by=self.request.user,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as exc:
            errors = exc.detail if hasattr(exc, 'detail') else {}
            if isinstance(errors, dict) and 'error' in errors:
                return Response(errors, status=status.HTTP_400_BAD_REQUEST)
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        self.perform_create(serializer)
        patient = serializer.instance
        output = PatientDetailSerializer(patient, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)

    @extend_schema(tags=['Patients'], summary='List patients')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=['Patients'], summary='Create a patient')
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class PatientDetailView(ClinicScopedMixin, RetrieveUpdateDestroyAPIView):
    queryset = Patient.objects.all()
    serializer_class = PatientDetailSerializer
    lookup_field = 'id'

    def get_permissions(self):
        if self.request.method in ('GET', 'HEAD', 'OPTIONS'):
            return [IsAnyClinicRole()]
        return [IsOwnerAdminOrReceptionist()]

    def perform_destroy(self, instance):
        instance.soft_delete()

    @extend_schema(exclude=True)
    def put(self, request, *args, **kwargs):
        """Disabled — use PATCH for partial updates."""
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    @extend_schema(tags=['Patients'], summary='Get patient details')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=['Patients'], summary='Update a patient')
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(tags=['Patients'], summary='Delete (soft) a patient')
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)
