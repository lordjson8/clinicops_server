from django.conf import settings
from django.db import models

from apps.core.models import TimestampedModel


class Visit(TimestampedModel):
    TYPE_CHOICES = [
        ('walkin', 'Walk-in'),
        ('appointment', 'Rendez-vous'),
        ('followup', 'Suivi'),
        ('emergency', 'Urgence'),
    ]

    STATUS_CHOICES = [
        ('open', 'Ouvert'),
        ('invoiced', 'Facture'),
        ('completed', 'Termine'),
        ('cancelled', 'Annule'),
    ]

    visit_id = models.CharField(max_length=20, unique=True, editable=False)
    clinic = models.ForeignKey(
        'clinics.Clinic', on_delete=models.CASCADE, related_name='visits',
    )
    patient = models.ForeignKey(
        'patients.Patient', on_delete=models.PROTECT, related_name='visits',
    )
    visit_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='walkin')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    notes = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='created_visits',
    )

    # Cancellation
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='cancelled_visits',
    )
    cancel_reason = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'visits'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['clinic', 'status']),
            models.Index(fields=['clinic', 'patient']),
            models.Index(fields=['clinic', '-created_at']),
        ]

    def save(self, *args, **kwargs):
        if not self.visit_id:
            from apps.core.id_generators import generate_visit_id
            self.visit_id = generate_visit_id(self.clinic_id)
        super().save(*args, **kwargs)

    @property
    def total(self):
        return sum(s.line_total for s in self.services.all())

    def __str__(self):
        return f'{self.visit_id} - {self.patient}'


class VisitService(TimestampedModel):
    visit = models.ForeignKey(
        Visit, on_delete=models.CASCADE, related_name='services',
    )
    service = models.ForeignKey(
        'clinics.Service', on_delete=models.PROTECT, related_name='visit_services',
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.IntegerField(help_text='Snapshot of service price at time of addition')
    price_override = models.IntegerField(null=True, blank=True)
    override_reason = models.TextField(blank=True, default='')
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='added_visit_services',
    )

    class Meta:
        db_table = 'visit_services'
        unique_together = ['visit', 'service']
        ordering = ['created_at']

    @property
    def line_total(self):
        price = self.price_override if self.price_override is not None else self.unit_price
        return price * self.quantity

    def __str__(self):
        return f'{self.service.name} x{self.quantity}'
