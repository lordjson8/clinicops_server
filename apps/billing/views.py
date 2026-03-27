from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView, GenericAPIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.core.mixins import ClinicScopedMixin
from apps.core.permissions import IsAnyClinicRole, IsOwnerOrAdmin, ReadAnyWriteRestricted
from apps.visits.models import Visit

from .models import Invoice, Payment
from .serializers import (
    InvoiceListSerializer, InvoiceDetailSerializer, InvoiceCreateSerializer, InvoiceVoidSerializer,
    PaymentListSerializer, PaymentCreateSerializer, PaymentVoidSerializer,
)
from .filters import InvoiceFilter, PaymentFilter
from .services import create_invoice_from_visit, record_payment, void_invoice, void_payment


# ──────────────────────────────────────────────
# Invoices
# ──────────────────────────────────────────────

class InvoiceListCreateView(ClinicScopedMixin, ListCreateAPIView):
    queryset = Invoice.objects.select_related('patient', 'created_by').prefetch_related('lines')
    permission_classes = [ReadAnyWriteRestricted]
    write_roles = ('owner', 'admin', 'receptionist')
    filter_backends = [InvoiceFilter]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return InvoiceListSerializer
        return InvoiceCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        clinic = request.user.clinic
        try:
            visit = Visit.objects.get(id=data['visitId'], clinic=clinic)
        except Visit.DoesNotExist:
            return Response(
                {'error': 'not_found', 'message': 'Visite introuvable.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            invoice = create_invoice_from_visit(
                visit=visit,
                created_by=request.user,
                discount_percent=data.get('discountPercent', 0),
                discount_amount=data.get('discountAmount', 0),
                discount_reason=data.get('discountReason', ''),
            )
        except ValueError as e:
            return Response(
                {'error': 'invoice_error', 'message': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        output = InvoiceDetailSerializer(invoice)
        return Response(output.data, status=status.HTTP_201_CREATED)

    @extend_schema(tags=['Invoices'], summary='List invoices')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=['Invoices'], summary='Create invoice from visit', request=InvoiceCreateSerializer, responses={201: InvoiceDetailSerializer})
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class InvoiceDetailView(ClinicScopedMixin, RetrieveAPIView):
    queryset = Invoice.objects.select_related(
        'patient', 'clinic', 'created_by', 'voided_by',
    ).prefetch_related('lines', 'payments')
    serializer_class = InvoiceDetailSerializer
    permission_classes = [IsAnyClinicRole]
    lookup_field = 'id'

    @extend_schema(tags=['Invoices'], summary='Get invoice details')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class InvoiceVoidView(GenericAPIView):
    """POST /invoices/<id>/void/"""
    serializer_class = InvoiceVoidSerializer
    permission_classes = [IsOwnerOrAdmin]

    @extend_schema(tags=['Invoices'], summary='Void an invoice', request=InvoiceVoidSerializer, responses={200: InvoiceDetailSerializer})
    def post(self, request, invoice_id):
        clinic = request.user.clinic
        try:
            invoice = Invoice.objects.get(id=invoice_id, clinic=clinic)
        except Invoice.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Facture introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            void_invoice(invoice, voided_by=request.user, reason=serializer.validated_data['reason'])
        except ValueError as e:
            return Response({'error': 'void_error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        output = InvoiceDetailSerializer(invoice)
        return Response(output.data)


# ──────────────────────────────────────────────
# Payments
# ──────────────────────────────────────────────

class PaymentListCreateView(ClinicScopedMixin, ListCreateAPIView):
    queryset = Payment.objects.select_related('invoice__patient', 'received_by').filter(status='confirmed')
    permission_classes = [ReadAnyWriteRestricted]
    write_roles = ('owner', 'admin', 'receptionist')
    filter_backends = [PaymentFilter]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return PaymentListSerializer
        return PaymentCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        clinic = request.user.clinic
        try:
            invoice = Invoice.objects.get(id=data['invoiceId'], clinic=clinic)
        except Invoice.DoesNotExist:
            return Response(
                {'error': 'not_found', 'message': 'Facture introuvable.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            payment = record_payment(
                invoice=invoice,
                amount=data['amount'],
                payment_method=data['method'],
                received_by=request.user,
                reference_number=data.get('referenceNumber', ''),
                notes=data.get('notes', ''),
            )
        except ValueError as e:
            return Response(
                {'error': 'payment_error', 'message': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        output = PaymentListSerializer(payment)
        return Response(output.data, status=status.HTTP_201_CREATED)

    @extend_schema(tags=['Payments'], summary='List payments')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=['Payments'], summary='Record a payment', request=PaymentCreateSerializer, responses={201: PaymentListSerializer})
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class PaymentVoidView(GenericAPIView):
    """POST /payments/<id>/void/"""
    serializer_class = PaymentVoidSerializer
    permission_classes = [IsOwnerOrAdmin]

    @extend_schema(tags=['Payments'], summary='Void a payment', request=PaymentVoidSerializer, responses={200: PaymentListSerializer})
    def post(self, request, payment_id):
        clinic = request.user.clinic
        try:
            payment = Payment.objects.get(id=payment_id, clinic=clinic)
        except Payment.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Paiement introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            void_payment(payment, voided_by=request.user, reason=serializer.validated_data['reason'])
        except ValueError as e:
            return Response({'error': 'void_error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        output = PaymentListSerializer(payment)
        return Response(output.data)
