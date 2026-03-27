from rest_framework import serializers

from .models import Clinic, Service


class ClinicSerializer(serializers.ModelSerializer):
    phonePrimary = serializers.CharField(source='phone_primary')
    phoneSecondary = serializers.CharField(source='phone_secondary', required=False, allow_blank=True)
    registrationNumber = serializers.CharField(source='registration_number', required=False, allow_blank=True)
    invoicePrefix = serializers.CharField(source='invoice_prefix', required=False)
    invoiceNumbering = serializers.CharField(source='invoice_numbering', required=False)
    invoiceFooter = serializers.CharField(source='invoice_footer', required=False, allow_blank=True)
    cashThreshold = serializers.IntegerField(source='cash_threshold', required=False)
    mtnMomoNumber = serializers.CharField(source='mtn_momo_number', required=False, allow_blank=True)
    orangeMoneyNumber = serializers.CharField(source='orange_money_number', required=False, allow_blank=True)
    bankName = serializers.CharField(source='bank_name', required=False, allow_blank=True)
    bankAccount = serializers.CharField(source='bank_account', required=False, allow_blank=True)
    isActive = serializers.BooleanField(source='is_active', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)

    class Meta:
        model = Clinic
        fields = [
            'id', 'name', 'address', 'city', 'region',
            'phonePrimary', 'phoneSecondary', 'email', 'registrationNumber',
            'invoicePrefix', 'invoiceNumbering', 'invoiceFooter', 'cashThreshold',
            'mtnMomoNumber', 'orangeMoneyNumber', 'bankName', 'bankAccount',
            'isActive', 'createdAt', 'updatedAt',
        ]
        read_only_fields = ['id', 'isActive', 'createdAt', 'updatedAt']


class ServiceSerializer(serializers.ModelSerializer):
    isActive = serializers.BooleanField(source='is_active', required=False)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)

    class Meta:
        model = Service
        fields = [
            'id', 'name', 'code', 'category', 'price',
            'description', 'isActive', 'createdAt', 'updatedAt',
        ]
        read_only_fields = ['id', 'createdAt', 'updatedAt']

    def validate_code(self, value):
        clinic = self.context['request'].user.clinic
        qs = Service.objects.filter(clinic=clinic, code=value)
        if self.instance:
            qs = qs.exclude(id=self.instance.id)
        if qs.exists():
            raise serializers.ValidationError("Un service avec ce code existe deja dans cette clinique.")
        return value

    def validate_name(self, value):
        clinic = self.context['request'].user.clinic
        qs = Service.objects.filter(clinic=clinic, name__iexact=value)
        if self.instance:
            qs = qs.exclude(id=self.instance.id)
        if qs.exists():
            raise serializers.ValidationError("Un service avec ce nom existe deja dans cette clinique.")
        return value

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Le prix ne peut pas etre negatif.")
        return value
