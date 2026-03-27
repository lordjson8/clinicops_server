from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from .models import User
from apps.core.utils import normalize_phone

STAFF_ROLE_CHOICES = [('admin', 'Administrateur'), ('receptionist', 'Receptionniste'), ('nurse', 'Infirmier(e)')]


class StaffListSerializer(serializers.ModelSerializer):
    firstName = serializers.CharField(source='first_name', read_only=True)
    lastName = serializers.CharField(source='last_name', read_only=True)
    isActive = serializers.BooleanField(source='is_active', read_only=True)
    lastLogin = serializers.DateTimeField(source='last_login', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'firstName', 'lastName', 'email', 'phone',
            'role', 'isActive', 'lastLogin', 'createdAt',
        ]


class StaffCreateSerializer(serializers.Serializer):
    firstName = serializers.CharField(max_length=100)
    lastName = serializers.CharField(max_length=100)
    phone = serializers.CharField(max_length=20)
    email = serializers.EmailField(required=False, allow_blank=True, default='')
    role = serializers.ChoiceField(choices=STAFF_ROLE_CHOICES)

    def validate_phone(self, value):
        normalized = normalize_phone(value)
        if User.objects.filter(phone=normalized).exists():
            raise serializers.ValidationError("Un utilisateur avec ce numero de telephone existe deja.")
        return normalized

    def validate_email(self, value):
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Un utilisateur avec cet email existe deja.")
        return value

    def validate_role(self, value):
        request = self.context.get('request')
        if not request:
            return value

        requester = request.user
        if value == 'admin' and requester.role != 'owner':
            raise serializers.ValidationError(
                "Seul le proprietaire peut creer un administrateur."
            )
        return value


class StaffUpdateSerializer(serializers.Serializer):
    firstName = serializers.CharField(max_length=100, required=False)
    lastName = serializers.CharField(max_length=100, required=False)
    phone = serializers.CharField(max_length=20, required=False)
    email = serializers.EmailField(required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=STAFF_ROLE_CHOICES, required=False)

    def validate_phone(self, value):
        normalized = normalize_phone(value)
        staff = self.context.get('staff')
        if staff and User.objects.filter(phone=normalized).exclude(id=staff.id).exists():
            raise serializers.ValidationError("Un utilisateur avec ce numero de telephone existe deja.")
        return normalized

    def validate_email(self, value):
        if not value:
            return value
        staff = self.context.get('staff')
        if staff and User.objects.filter(email=value).exclude(id=staff.id).exists():
            raise serializers.ValidationError("Un utilisateur avec cet email existe deja.")
        return value

    def validate_role(self, value):
        request = self.context.get('request')
        if not request:
            return value
        if value == 'admin' and request.user.role != 'owner':
            raise serializers.ValidationError(
                "Seul le proprietaire peut attribuer le role d'administrateur."
            )
        return value
