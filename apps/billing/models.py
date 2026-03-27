from django.conf import settings
from django.db import models

from apps.core.models import TimestampedModel


class Invoice(TimestampedModel):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('partial', 'Partiellement paye'),
        ('paid', 'Paye'),
        ('cancelled', 'Annule'),
    ]

    invoice_number = models.CharField(max_length=20, unique=True, editable=False)
    visit = models.OneToOneField(
        'visits.Visit', on_delete=models.PROTECT, related_name='invoice',
    )
    patient = models.ForeignKey(
        'patients.Patient', on_delete=models.PROTECT, related_name='invoices',
    )
    clinic = models.ForeignKey(
        'clinics.Clinic', on_delete=models.CASCADE, related_name='invoices',
    )

    subtotal = models.IntegerField(default=0)
    discount_percent = models.IntegerField(default=0)
    discount_amount = models.IntegerField(default=0)
    discount_reason = models.TextField(blank=True, default='')
    total = models.IntegerField(default=0)
    paid_amount = models.IntegerField(default=0)
    balance = models.IntegerField(default=0)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    issued_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='created_invoices',
    )

    # Void
    voided_at = models.DateTimeField(null=True, blank=True)
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='voided_invoices',
    )
    void_reason = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'invoices'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['clinic', 'status']),
            models.Index(fields=['clinic', 'patient']),
            models.Index(fields=['clinic', 'invoice_number']),
        ]

    def __str__(self):
        return f'{self.invoice_number} - {self.total} XAF'


class InvoiceLine(TimestampedModel):
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name='lines',
    )
    visit_service = models.ForeignKey(
        'visits.VisitService', on_delete=models.PROTECT,
        null=True, blank=True, related_name='invoice_lines',
    )
    name = models.CharField(max_length=200)
    quantity = models.IntegerField()
    unit_price = models.IntegerField()
    total = models.IntegerField()

    class Meta:
        db_table = 'invoice_lines'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.name} x{self.quantity}'


class Payment(TimestampedModel):
    METHOD_CHOICES = [
        ('cash', 'Especes'),
        ('mtn_momo', 'MTN MoMo'),
        ('orange_money', 'Orange Money'),
        ('bank_transfer', 'Virement bancaire'),
    ]

    STATUS_CHOICES = [
        ('confirmed', 'Confirme'),
        ('voided', 'Annule'),
    ]

    payment_id = models.CharField(max_length=20, unique=True, editable=False)
    invoice = models.ForeignKey(
        Invoice, on_delete=models.PROTECT, related_name='payments',
    )
    clinic = models.ForeignKey(
        'clinics.Clinic', on_delete=models.CASCADE, related_name='payments',
    )
    amount = models.IntegerField()
    payment_method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    reference_number = models.CharField(max_length=100, blank=True, default='')
    payment_date = models.DateTimeField()
    notes = models.TextField(blank=True, default='')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='received_payments',
    )

    # Void
    voided_at = models.DateTimeField(null=True, blank=True)
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='voided_payments',
    )
    void_reason = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['clinic', 'invoice']),
            models.Index(fields=['clinic', 'payment_method']),
        ]

    def __str__(self):
        return f'{self.payment_id} - {self.amount} XAF'
