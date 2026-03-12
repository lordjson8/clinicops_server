import uuid
from django.db import models
from django.utils import timezone


def generate_patient_id():
    today = timezone.now()
    prefix = f"PAT-{today.strftime('%Y%m%d')}"
    count = Patient.objects.filter(patient_id__startswith=prefix).count()
    return f"{prefix}-{str(count + 1).zfill(3)}"


class Patient(models.Model):
    GENDER_CHOICES = [("M", "Male"), ("F", "Female"), ("O", "Other")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient_id = models.CharField(max_length=20, unique=True, editable=False)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    phone_secondary = models.CharField(max_length=20, blank=True, default="")
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    address = models.TextField(blank=True, default="")
    emergency_contact_name = models.CharField(max_length=255, blank=True, default="")
    emergency_contact_phone = models.CharField(max_length=20, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    outstanding_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["phone"]),
            models.Index(fields=["patient_id"]),
            models.Index(fields=["name"]),
        ]

    def save(self, *args, **kwargs):
        if not self.patient_id:
            self.patient_id = generate_patient_id()
        super().save(*args, **kwargs)

    @property
    def last_visit(self):
        visit = self.visits.order_by("-visit_date").first()
        return visit.visit_date if visit else None

    def __str__(self):
        return f"{self.patient_id} - {self.name}"