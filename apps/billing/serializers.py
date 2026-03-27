from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from .models import Invoice, InvoiceLine, Payment


# ──────────────────────────────────────────────
# Invoice serializers
# ──────────────────────────────────────────────

class InvoiceLineSerializer(serializers.ModelSerializer):
    unitPrice = serializers.IntegerField(source='unit_price', read_only=True)

    class Meta:
        model = InvoiceLine
        fields = ['id', 'name', 'quantity', 'unitPrice', 'total']


class PaymentNestedSerializer(serializers.ModelSerializer):
    """Compact payment serializer for embedding inside invoice detail."""
    date = serializers.DateTimeField(source='payment_date', read_only=True)
    method = serializers.CharField(source='payment_method', read_only=True)
    reference = serializers.CharField(source='reference_number', read_only=True)

    class Meta:
        model = Payment
        fields = ['id', 'date', 'method', 'amount', 'reference']


class InvoiceListSerializer(serializers.ModelSerializer):
    invoiceNumber = serializers.CharField(source='invoice_number', read_only=True)
    date = serializers.DateTimeField(source='issued_at', read_only=True)
    patient = serializers.CharField(source='patient.full_name', read_only=True)
    paidAmount = serializers.IntegerField(source='paid_amount', read_only=True)
    services = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoiceNumber', 'date', 'patient', 'services',
            'total', 'paidAmount', 'balance', 'status',
        ]

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_services(self, obj):
        return list(obj.lines.values_list('name', flat=True))


class InvoiceDetailSerializer(serializers.ModelSerializer):
    invoiceNumber = serializers.CharField(source='invoice_number', read_only=True)
    date = serializers.DateTimeField(source='issued_at', read_only=True)
    patient = serializers.SerializerMethodField()
    items = InvoiceLineSerializer(source='lines', many=True, read_only=True)
    paidAmount = serializers.IntegerField(source='paid_amount', read_only=True)
    payments = PaymentNestedSerializer(many=True, read_only=True)
    clinic = serializers.SerializerMethodField()
    discountPercent = serializers.IntegerField(source='discount_percent', read_only=True)
    discountAmount = serializers.IntegerField(source='discount_amount', read_only=True)
    discountReason = serializers.CharField(source='discount_reason', read_only=True)
    createdBy = serializers.CharField(source='created_by.full_name', read_only=True)
    voidedAt = serializers.DateTimeField(source='voided_at', read_only=True)
    voidedBy = serializers.SerializerMethodField()
    voidReason = serializers.CharField(source='void_reason', read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoiceNumber', 'date', 'patient', 'items',
            'subtotal', 'discountPercent', 'discountAmount', 'discountReason',
            'total', 'paidAmount', 'balance', 'status',
            'payments', 'clinic', 'createdBy',
            'voidedAt', 'voidedBy', 'voidReason',
        ]

    @extend_schema_field({'type': 'object', 'properties': {'id': {'type': 'string'}, 'name': {'type': 'string'}, 'phone': {'type': 'string'}}})
    def get_patient(self, obj):
        return {
            'id': str(obj.patient.id),
            'name': obj.patient.full_name,
            'phone': obj.patient.phone,
        }

    @extend_schema_field({'type': 'object', 'properties': {'name': {'type': 'string'}, 'address': {'type': 'string'}, 'phone': {'type': 'string'}}})
    def get_clinic(self, obj):
        c = obj.clinic
        return {
            'name': c.name,
            'address': c.address,
            'phone': c.phone_primary,
        }

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_voidedBy(self, obj):
        if obj.voided_by:
            return obj.voided_by.full_name
        return None


class InvoiceCreateSerializer(serializers.Serializer):
    visitId = serializers.UUIDField()
    discountPercent = serializers.IntegerField(required=False, default=0, min_value=0, max_value=100)
    discountAmount = serializers.IntegerField(required=False, default=0, min_value=0)
    discountReason = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, data):
        has_discount = data.get('discountPercent', 0) > 0 or data.get('discountAmount', 0) > 0
        if has_discount and not data.get('discountReason'):
            raise serializers.ValidationError(
                {'discountReason': "La raison est requise lorsqu'une remise est appliquee."}
            )
        # Only owner/admin can apply discounts
        request = self.context.get('request')
        if has_discount and request and request.user.role not in ('owner', 'admin'):
            raise serializers.ValidationError(
                {'discountPercent': "Seuls le proprietaire et l'administrateur peuvent appliquer des remises."}
            )
        return data


class InvoiceVoidSerializer(serializers.Serializer):
    reason = serializers.CharField()

    def validate_reason(self, value):
        if not value.strip():
            raise serializers.ValidationError("La raison est requise.")
        return value


# ──────────────────────────────────────────────
# Payment serializers
# ──────────────────────────────────────────────

class PaymentListSerializer(serializers.ModelSerializer):
    paymentId = serializers.CharField(source='payment_id', read_only=True)
    date = serializers.DateTimeField(source='payment_date', read_only=True)
    patient = serializers.CharField(source='invoice.patient.full_name', read_only=True)
    invoiceNumber = serializers.CharField(source='invoice.invoice_number', read_only=True)
    method = serializers.CharField(source='payment_method', read_only=True)
    staffName = serializers.CharField(source='received_by.full_name', read_only=True)
    reference = serializers.CharField(source='reference_number', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'paymentId', 'date', 'patient', 'invoiceNumber',
            'method', 'amount', 'staffName', 'reference',
        ]


class PaymentCreateSerializer(serializers.Serializer):
    invoiceId = serializers.UUIDField()
    amount = serializers.IntegerField(min_value=1)
    method = serializers.ChoiceField(choices=['cash', 'mtn_momo', 'orange_money', 'bank_transfer'])
    referenceNumber = serializers.CharField(required=False, allow_blank=True, default='')
    notes = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, data):
        if data['method'] == 'bank_transfer' and not data.get('referenceNumber'):
            raise serializers.ValidationError(
                {'referenceNumber': "Le numero de reference est requis pour un virement bancaire."}
            )
        return data


class PaymentVoidSerializer(serializers.Serializer):
    reason = serializers.CharField()

    def validate_reason(self, value):
        if not value.strip():
            raise serializers.ValidationError("La raison est requise.")
        return value
