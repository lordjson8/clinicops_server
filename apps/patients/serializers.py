from rest_framework import serializers

from .models import Patient


class PatientListSerializer(serializers.ModelSerializer):
    patientId = serializers.CharField(source='patient_id', read_only=True)
    firstName = serializers.CharField(source='first_name')
    lastName = serializers.CharField(source='last_name')
    dateOfBirth = serializers.DateField(source='date_of_birth', required=False, allow_null=True)
    lastVisit = serializers.DateField(source='last_visit', read_only=True)
    outstandingBalance = serializers.IntegerField(source='outstanding_balance', read_only=True)

    class Meta:
        model = Patient
        fields = [
            'id', 'patientId', 'firstName', 'lastName', 'phone',
            'dateOfBirth', 'gender', 'lastVisit', 'outstandingBalance',
        ]


class PatientDetailSerializer(serializers.ModelSerializer):
    patientId = serializers.CharField(source='patient_id', read_only=True)
    firstName = serializers.CharField(source='first_name')
    lastName = serializers.CharField(source='last_name')
    phoneSecondary = serializers.CharField(source='phone_secondary', required=False, allow_blank=True)
    dateOfBirth = serializers.DateField(source='date_of_birth', required=False, allow_null=True)
    emergencyContactName = serializers.CharField(source='emergency_contact_name', required=False, allow_blank=True)
    emergencyContactPhone = serializers.CharField(source='emergency_contact_phone', required=False, allow_blank=True)
    outstandingBalance = serializers.IntegerField(source='outstanding_balance', read_only=True)
    lastVisit = serializers.DateField(source='last_visit', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)
    forceCreate = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = Patient
        fields = [
            'id', 'patientId', 'firstName', 'lastName', 'phone', 'phoneSecondary',
            'dateOfBirth', 'gender', 'address',
            'emergencyContactName', 'emergencyContactPhone',
            'notes', 'outstandingBalance', 'lastVisit',
            'createdAt', 'updatedAt', 'forceCreate',
        ]
        read_only_fields = ['id', 'patientId', 'createdAt', 'updatedAt', 'outstandingBalance']

    def validate(self, data):
        force_create = data.pop('forceCreate', False) if 'forceCreate' in data else data.pop('force_create', False)
        phone = data.get('phone')

        if phone and not force_create:
            clinic = self.context['request'].user.clinic
            qs = Patient.objects.filter(clinic=clinic, phone=phone)
            if self.instance:
                qs = qs.exclude(id=self.instance.id)
            existing = qs.first()
            if existing:
                raise serializers.ValidationError({
                    'error': 'duplicate_phone',
                    'message': 'Un patient avec ce numero existe deja',
                    'existing_patient': {
                        'id': str(existing.id),
                        'name': existing.full_name[:8] + '.' if len(existing.full_name) > 8 else existing.full_name,
                        'patient_id': existing.patient_id,
                    },
                })

        return data
