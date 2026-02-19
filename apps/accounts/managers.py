from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):
    """
    Custom user manager. Phone is the unique identifier for authentication.
    """

    def create_user(self, phone, first_name, last_name, role, clinic, password=None, **extra_fields):
        if not phone:
            raise ValueError('Le numero de telephone est obligatoire.')

        from apps.core.utils import normalize_phone
        phone = normalize_phone(phone)

        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        print(phone, first_name, last_name, password, role)
        
        user = self.model(
            phone=phone,
            first_name=first_name,
            last_name=last_name,
            role=role,
            clinic=clinic,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, first_name, last_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'owner')
        extra_fields.setdefault('must_change_password', False)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        # Superuser needs a clinic — get or create a default one
        from apps.clinics.models import Clinic
        clinic, _ = Clinic.objects.get_or_create(
            name='System',
            defaults={'phone_primary': '+237000000000'},
        )
        
        print(phone, first_name, last_name, password)
        return self.create_user(
            phone=phone,
            first_name=first_name,
            last_name=last_name,
            # role='owner',
            clinic=clinic,
            password=password,
            **extra_fields,
        )