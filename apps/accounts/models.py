import uuid
from datetime import timedelta

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('owner', 'Proprietaire'),
        ('admin', 'Administrateur'),
        ('receptionist', 'Receptionniste'),
        ('nurse', 'Infirmier(e)'),
    ]

    ROLE_HIERARCHY = {
        'owner': 4,
        'admin': 3,
        'receptionist': 2,
        'nurse': 1,
    }

    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Auth — phone is the login field
    phone = models.CharField(max_length=20, unique=True, db_index=True)
    email = models.EmailField(blank=True, default='')

    # Profile
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    clinic = models.ForeignKey(
        'clinics.Clinic',
        on_delete=models.CASCADE,
        related_name='users',
    )

    # Status
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    must_change_password = models.BooleanField(default=True)

    # Security — login attempts & lockout
    failed_login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)

    # SMS password reset
    reset_code = models.CharField(max_length=6, blank=True, default='')
    reset_code_expires = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['clinic', 'role']),
            models.Index(fields=['clinic', 'is_active']),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.phone})"

    # ---- Properties ----

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def is_locked(self):
        if self.locked_until and self.locked_until > timezone.now():
            return True
        return False

    @property
    def role_level(self):
        return self.ROLE_HIERARCHY.get(self.role, 0)

    # ---- Security methods ----

    def lock_account(self, duration_minutes=15):
        self.locked_until = timezone.now() + timedelta(minutes=duration_minutes)
        self.save(update_fields=['locked_until'])

    def reset_failed_attempts(self):
        self.failed_login_attempts = 0
        self.locked_until = None
        self.save(update_fields=['failed_login_attempts', 'locked_until'])

    def increment_failed_attempts(self):
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            self.lock_account()
        self.save(update_fields=['failed_login_attempts', 'locked_until'])

    # ---- Reset code methods ----

    def set_reset_code(self, code):
        self.reset_code = code
        self.reset_code_expires = timezone.now() + timedelta(minutes=15)
        self.save(update_fields=['reset_code', 'reset_code_expires'])

    def clear_reset_code(self):
        self.reset_code = ''
        self.reset_code_expires = None
        self.save(update_fields=['reset_code', 'reset_code_expires'])

    def verify_reset_code(self, code):
        if not self.reset_code or not self.reset_code_expires:
            return False
        if self.reset_code_expires < timezone.now():
            return False
        return self.reset_code == code