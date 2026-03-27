from django.utils import timezone
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from .models import Visit, VisitService
from apps.clinics.models import Service


# ──────────────────────────────────────────────
# VisitService serializers
# ──────────────────────────────────────────────

class VisitServiceReadSerializer(serializers.ModelSerializer):
    serviceId = serializers.UUIDField(source='service.id', read_only=True)
    serviceName = serializers.CharField(source='service.name', read_only=True)
    unitPrice = serializers.IntegerField(source='unit_price', read_only=True)
    priceOverride = serializers.IntegerField(source='price_override', read_only=True)
    overrideReason = serializers.CharField(source='override_reason', read_only=True)
    lineTotal = serializers.IntegerField(source='line_total', read_only=True)
    addedBy = serializers.CharField(source='added_by.full_name', read_only=True)

    class Meta:
        model = VisitService
        fields = [
            'id', 'serviceId', 'serviceName', 'quantity',
            'unitPrice', 'priceOverride', 'overrideReason', 'lineTotal', 'addedBy',
        ]


class VisitServiceCreateSerializer(serializers.Serializer):
    serviceId = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, default=1)
    priceOverride = serializers.IntegerField(required=False, allow_null=True)
    overrideReason = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, data):
        if data.get('priceOverride') is not None and not data.get('overrideReason'):
            raise serializers.ValidationError(
                {'overrideReason': "La raison est requise pour un prix personnalise."}
            )
        # Check price override permission
        request = self.context.get('request')
        if data.get('priceOverride') is not None and request:
            if request.user.role not in ('owner', 'admin'):
                raise serializers.ValidationError(
                    {'priceOverride': "Seuls le proprietaire et l'administrateur peuvent modifier le prix."}
                )
        return data


# ──────────────────────────────────────────────
# Visit serializers
# ──────────────────────────────────────────────

class VisitListSerializer(serializers.ModelSerializer):
    visitId = serializers.CharField(source='visit_id', read_only=True)
    date = serializers.DateTimeField(source='created_at', read_only=True)
    patient = serializers.CharField(source='patient.full_name', read_only=True)
    patientId = serializers.UUIDField(source='patient.id', read_only=True)
    services = serializers.SerializerMethodField()
    total = serializers.IntegerField(read_only=True)
    staffName = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model = Visit
        fields = [
            'id', 'visitId', 'date', 'patient', 'patientId',
            'services', 'total', 'status', 'staffName',
        ]

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_services(self, obj):
        return list(obj.services.values_list('service__name', flat=True))


class VisitDetailSerializer(serializers.ModelSerializer):
    visitId = serializers.CharField(source='visit_id', read_only=True)
    visitType = serializers.CharField(source='visit_type', read_only=True)
    date = serializers.DateTimeField(source='created_at', read_only=True)
    patient = serializers.SerializerMethodField()
    services = VisitServiceReadSerializer(many=True, read_only=True)
    total = serializers.IntegerField(read_only=True)
    staffName = serializers.CharField(source='created_by.full_name', read_only=True)
    invoice = serializers.SerializerMethodField()
    cancelledAt = serializers.DateTimeField(source='cancelled_at', read_only=True)
    cancelledBy = serializers.SerializerMethodField()
    cancelReason = serializers.CharField(source='cancel_reason', read_only=True)

    class Meta:
        model = Visit
        fields = [
            'id', 'visitId', 'visitType', 'date', 'patient',
            'services', 'total', 'status', 'staffName', 'notes',
            'invoice', 'cancelledAt', 'cancelledBy', 'cancelReason',
        ]

    @extend_schema_field({'type': 'object', 'properties': {'id': {'type': 'string'}, 'name': {'type': 'string'}, 'phone': {'type': 'string'}, 'patientId': {'type': 'string'}}})
    def get_patient(self, obj):
        return {
            'id': str(obj.patient.id),
            'name': obj.patient.full_name,
            'phone': obj.patient.phone,
            'patientId': obj.patient.patient_id,
        }

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_invoice(self, obj):
        try:
            inv = obj.invoice
        except Exception:
            return None
        return str(inv.invoice_number) if inv else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_cancelledBy(self, obj):
        if obj.cancelled_by:
            return obj.cancelled_by.full_name
        return None


class VisitCreateSerializer(serializers.Serializer):
    patientId = serializers.UUIDField()
    visitType = serializers.ChoiceField(
        choices=['walkin', 'appointment', 'followup', 'emergency'],
        default='walkin',
    )
    notes = serializers.CharField(required=False, allow_blank=True, default='')
    services = VisitServiceCreateSerializer(many=True, required=False, default=[])

    def validate_patientId(self, value):
        from apps.patients.models import Patient
        clinic = self.context['request'].user.clinic
        if not Patient.objects.filter(id=value, clinic=clinic).exists():
            raise serializers.ValidationError("Patient introuvable dans cette clinique.")
        return value

    def create(self, validated_data):
        from apps.patients.models import Patient
        request = self.context['request']
        clinic = request.user.clinic
        patient = Patient.objects.get(id=validated_data['patientId'], clinic=clinic)

        visit = Visit.objects.create(
            clinic=clinic,
            patient=patient,
            visit_type=validated_data['visitType'],
            notes=validated_data.get('notes', ''),
            created_by=request.user,
        )

        for svc_data in validated_data.get('services', []):
            service = Service.objects.get(id=svc_data['serviceId'], clinic=clinic)
            VisitService.objects.create(
                visit=visit,
                service=service,
                quantity=svc_data.get('quantity', 1),
                unit_price=service.price,
                price_override=svc_data.get('priceOverride'),
                override_reason=svc_data.get('overrideReason', ''),
                added_by=request.user,
            )

        return visit


class VisitCancelSerializer(serializers.Serializer):
    reason = serializers.CharField()

    def validate_reason(self, value):
        if not value.strip():
            raise serializers.ValidationError("La raison d'annulation est requise.")
        return value
