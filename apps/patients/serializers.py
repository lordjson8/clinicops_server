from rest_framework import serializers
from .models import Patient


class PatientListSerializer(serializers.ModelSerializer):
    last_visit = serializers.DateField(read_only=True)

    class Meta:
        model = Patient
        fields = [
            "id", "patient_id", "name", "phone",
            "date_of_birth", "gender", "last_visit", "outstanding_balance",
        ]


class PatientDetailSerializer(serializers.ModelSerializer):
    last_visit = serializers.DateField(read_only=True)
    force_create = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = Patient
        fields = [
            "id", "patient_id", "name", "phone", "phone_secondary",
            "date_of_birth", "gender", "address",
            "emergency_contact_name", "emergency_contact_phone",
            "notes", "outstanding_balance", "last_visit",
            "created_at", "updated_at", "force_create",
        ]
        read_only_fields = ["id", "patient_id", "created_at", "updated_at", "outstanding_balance"]

    def validate(self, data):
        force_create = data.pop("force_create", False)
        phone = data.get("phone")

        if phone and not force_create:
            existing = Patient.objects.filter(phone=phone).first()
            if existing:
                raise serializers.ValidationError({
                    "error": "duplicate_phone",
                    "message": "Un patient avec ce numero existe deja",
                    "existing_patient": {
                        "id": str(existing.id),
                        "name": existing.name[:8] + "." if len(existing.name) > 8 else existing.name,
                        "patient_id": existing.patient_id,
                    },
                })

        return data