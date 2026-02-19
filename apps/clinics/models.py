from apps.core.models import TimestampedModel, SoftDeleteModel
from django.db import models


class Clinic(TimestampedModel):
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True, default='')
    city = models.CharField(max_length=100, blank=True, default='')
    region = models.CharField(max_length=100, blank=True, default='')
    phone_primary = models.CharField(max_length=20)
    phone_secondary = models.CharField(max_length=20, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    # logo = models.ImageField(upload_to='clinic_logos/', null=True, blank=True)
    registration_number = models.CharField(max_length=50, blank=True, default='')

    # Invoice settings
    invoice_prefix = models.CharField(max_length=10, default='INV-')
    invoice_numbering = models.CharField(
        max_length=20,
        choices=[
            ('daily', 'Daily Reset'),
            ('monthly', 'Monthly'),
            ('continuous', 'Continuous'),
        ],
        default='continuous',
    )
    invoice_footer = models.TextField(blank=True, default='')
    cash_threshold = models.IntegerField(default=500)

    # Payment method settings (displayed on invoices, used in settings page)
    mtn_momo_number = models.CharField(max_length=20, blank=True, default='')
    orange_money_number = models.CharField(max_length=20, blank=True, default='')
    bank_name = models.CharField(max_length=100, blank=True, default='')
    bank_account = models.CharField(max_length=50, blank=True, default='')

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'clinics'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Service(SoftDeleteModel):
    CATEGORY_CHOICES = [
        ('consultation', 'Consultation'),
        ('laboratory', 'Laboratoire'),
        ('pharmacy', 'Pharmacie'),
        ('care', 'Soins'),
    ]

    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='services')
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    price = models.IntegerField()  # XAF — no decimals
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'services'
        unique_together = ['clinic', 'code']
        ordering = ['category', 'name']
        indexes = [
            models.Index(fields=['clinic', 'category']),
            models.Index(fields=['clinic', 'is_active', 'is_deleted']),
        ]

    def __str__(self):
        return f"{self.name} ({self.price} XAF)"