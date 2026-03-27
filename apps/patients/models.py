from django.conf import settings
from django.db import models

from apps.core.models import SoftDeleteModel


class Patient(SoftDeleteModel):
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female'), ('O', 'Other')]

    clinic = models.ForeignKey(
        'clinics.Clinic', on_delete=models.CASCADE, related_name='patients',
    )
    patient_id = models.CharField(max_length=20, unique=True, editable=False)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    phone_secondary = models.CharField(max_length=20, blank=True, default='')
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    address = models.TextField(blank=True, default='')
    emergency_contact_name = models.CharField(max_length=255, blank=True, default='')
    emergency_contact_phone = models.CharField(max_length=20, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    outstanding_balance = models.IntegerField(default=0)
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='registered_patients',
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['clinic', 'phone']),
            models.Index(fields=['clinic', 'patient_id']),
            models.Index(fields=['clinic', 'last_name', 'first_name']),
        ]

    def save(self, *args, **kwargs):
        if not self.patient_id:
            from apps.core.id_generators import generate_patient_id
            self.patient_id = generate_patient_id(self.clinic_id)
        super().save(*args, **kwargs)

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    @property
    def last_visit(self):
        visit = self.visits.order_by('-created_at').first()
        return visit.created_at.date() if visit else None

    def __str__(self):
        return f'{self.patient_id} - {self.full_name}'
