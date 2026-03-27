from django.utils import timezone
from rest_framework import serializers as drf_serializers, status
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView, GenericAPIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, inline_serializer

from apps.core.mixins import ClinicScopedMixin
from apps.core.permissions import (
    IsAnyClinicRole, IsOwnerOrAdmin, IsOwnerAdminOrReceptionist, ReadAnyWriteRestricted,
)
from apps.clinics.models import Service

from .models import Visit, VisitService
from .serializers import (
    VisitListSerializer, VisitDetailSerializer, VisitCreateSerializer,
    VisitServiceCreateSerializer, VisitServiceReadSerializer, VisitCancelSerializer,
)
from .filters import VisitFilter


class VisitListCreateView(ClinicScopedMixin, ListCreateAPIView):
    queryset = Visit.objects.select_related('patient', 'created_by').prefetch_related('services__service')
    permission_classes = [ReadAnyWriteRestricted]
    write_roles = ('owner', 'admin', 'receptionist')
    filter_backends = [VisitFilter]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return VisitListSerializer
        return VisitCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        visit = serializer.save()
        output = VisitDetailSerializer(visit, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)

    @extend_schema(tags=['Visits'], summary='List visits')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=['Visits'], summary='Create a visit', request=VisitCreateSerializer, responses={201: VisitDetailSerializer})
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class VisitDetailView(ClinicScopedMixin, RetrieveAPIView):
    queryset = Visit.objects.select_related('patient', 'created_by', 'cancelled_by').prefetch_related('services__service')
    serializer_class = VisitDetailSerializer
    permission_classes = [IsAnyClinicRole]
    lookup_field = 'id'

    @extend_schema(tags=['Visits'], summary='Get visit details')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class VisitAddServiceView(GenericAPIView):
    """POST /visits/<id>/services/ — add a service to an open visit."""
    serializer_class = VisitServiceCreateSerializer
    permission_classes = [IsAnyClinicRole]

    @extend_schema(tags=['Visits'], summary='Add service to visit', request=VisitServiceCreateSerializer, responses={201: VisitServiceReadSerializer})
    def post(self, request, visit_id):
        clinic = request.user.clinic
        try:
            visit = Visit.objects.get(id=visit_id, clinic=clinic)
        except Visit.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Visite introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        if visit.status != 'open':
            return Response(
                {'error': 'visit_not_open', 'message': 'Les services ne peuvent etre ajoutes qu\'a une visite ouverte.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            service = Service.objects.get(id=data['serviceId'], clinic=clinic, is_active=True, is_deleted=False)
        except Service.DoesNotExist:
            return Response({'error': 'service_not_found', 'message': 'Service introuvable ou inactif.'}, status=status.HTTP_404_NOT_FOUND)

        if VisitService.objects.filter(visit=visit, service=service).exists():
            return Response({'error': 'duplicate_service', 'message': 'Ce service est deja ajoute a cette visite.'}, status=status.HTTP_400_BAD_REQUEST)

        vs = VisitService.objects.create(
            visit=visit,
            service=service,
            quantity=data.get('quantity', 1),
            unit_price=service.price,
            price_override=data.get('priceOverride'),
            override_reason=data.get('overrideReason', ''),
            added_by=request.user,
        )

        output = VisitServiceReadSerializer(vs)
        return Response(output.data, status=status.HTTP_201_CREATED)


class VisitRemoveServiceView(GenericAPIView):
    """DELETE /visits/<visit_id>/services/<service_id>/ — remove a service from an open visit."""
    permission_classes = [IsOwnerAdminOrReceptionist]
    serializer_class = inline_serializer('EmptyVisitService', fields={})

    @extend_schema(tags=['Visits'], summary='Remove service from visit', responses={204: None})
    def delete(self, request, visit_id, service_id):
        clinic = request.user.clinic
        try:
            visit = Visit.objects.get(id=visit_id, clinic=clinic)
        except Visit.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Visite introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        if visit.status != 'open':
            return Response(
                {'error': 'visit_not_open', 'message': 'Les services ne peuvent etre retires que d\'une visite ouverte.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            vs = VisitService.objects.get(id=service_id, visit=visit)
        except VisitService.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Service de visite introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        # Receptionist can only remove services they added, same day
        if request.user.role == 'receptionist':
            if vs.added_by != request.user:
                return Response(
                    {'error': 'forbidden', 'message': 'Vous ne pouvez retirer que les services que vous avez ajoutes.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if vs.created_at.date() != timezone.localdate():
                return Response(
                    {'error': 'forbidden', 'message': 'Vous ne pouvez retirer les services que le jour meme.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        vs.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class VisitCancelView(GenericAPIView):
    """POST /visits/<id>/cancel/ — cancel an open visit."""
    serializer_class = VisitCancelSerializer
    permission_classes = [IsOwnerOrAdmin]

    @extend_schema(tags=['Visits'], summary='Cancel a visit', request=VisitCancelSerializer, responses={200: VisitDetailSerializer})
    def post(self, request, visit_id):
        clinic = request.user.clinic
        try:
            visit = Visit.objects.get(id=visit_id, clinic=clinic)
        except Visit.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Visite introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        if visit.status in ('completed', 'cancelled'):
            return Response(
                {'error': 'invalid_status', 'message': f'Impossible d\'annuler une visite avec le statut "{visit.status}".'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        visit.status = 'cancelled'
        visit.cancelled_at = timezone.now()
        visit.cancelled_by = request.user
        visit.cancel_reason = serializer.validated_data['reason']
        visit.save(update_fields=['status', 'cancelled_at', 'cancelled_by', 'cancel_reason', 'updated_at'])

        output = VisitDetailSerializer(visit, context=self.get_serializer_context())
        return Response(output.data)
