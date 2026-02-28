from rest_framework import serializers

from .models import User

class UserSerializer(serializers.ModelSerializer):

    firstName= serializers.CharField(source="first_name")
    lastName= serializers.CharField(source="last_name")
    mustChangePassword= serializers.BooleanField(source='must_change_password', read_only=True)
    clinic= serializers.SerializerMethodField()

    class Meta:
        model= User
        fields = [
            'id', 'firstName','lastName' ,'phone', 'email','role' , 'clinic','mustChangePassword'
        ]

    read_only_fields = ['id', 'role', 'clinic', 'mustChangePassword']

    def get_clinic(self, obj):
        return {
            'id': str(obj.clinic_id),
            'name': obj.clinic.name,
        }
    
class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)
    remember_me = serializers.BooleanField(default=False, required=False)


class ClinicRegistrationSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    address = serializers.CharField(required=False, default='', allow_blank= True)
    phone = serializers.CharField(max_length=20)
    email = serializers.EmailField(required=False, default='',allow_blank= True)
    

class AdminRegistrationSerializer(serializers.Serializer):
    firstName = serializers.CharField(max_length=100)
    lastName = serializers.CharField(max_length=100)
    phone = serializers.CharField(max_length=20)
    email = serializers.EmailField(required=False, default='', allow_blank=True)
    password = serializers.CharField(min_length=8, write_only=True)
    passwordConfirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['password'] != attrs['passwordConfirm']:
            raise serializers.ValidationError({
                'passwordConfirm': 'Les mots de passe ne correspondent pas.'
            })
        return attrs
    
class RegisterSerializer(serializers.Serializer):
    clinic = ClinicRegistrationSerializer()
    admin = AdminRegistrationSerializer()

    def validate(self, attrs):
        phone = attrs['admin']['phone']
        from apps.core.utils import normalize_phone
        normalized = normalize_phone(phone)

        if User.objects.filter(phone=normalized).exists():
            raise serializers.ValidationError({
                'admin': {'phone': ['Un compte avec ce numero existe deja.']}
            })

        # Store normalized phone back
        attrs['admin']['phone'] = normalized
        attrs['clinic']['phone'] = normalize_phone(attrs['clinic']['phone'])
        return attrs
    


class PasswordResetRequestSerializer(serializers.Serializer):
    phone = serializers.CharField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    phone = serializers.CharField()
    code = serializers.CharField(max_length=6, min_length=6)
    password = serializers.CharField(min_length=8, write_only=True)
    passwordConfirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['password'] != attrs['passwordConfirm']:
            raise serializers.ValidationError({
                'passwordConfirm': 'Les mots de passe ne correspondent pas.'
            })
        return attrs



class ChangePasswordSerializer(serializers.Serializer):
    currentPassword = serializers.CharField(write_only=True)
    newPassword = serializers.CharField(min_length=8, write_only=True)
    newPasswordConfirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['newPassword'] != attrs['newPasswordConfirm']:
            raise serializers.ValidationError({
                'newPasswordConfirm': 'Les mots de passe ne correspondent pas.'
            })
        return attrs


class UpdateProfileSerializer(serializers.Serializer):
    firstName = serializers.CharField(max_length=100, required=False)
    lastName = serializers.CharField(max_length=100, required=False)
    phone = serializers.CharField(max_length=20, required=False)
    email = serializers.EmailField(required=False, allow_blank=True)

    def validate_phone(self, value):
        from apps.core.utils import normalize_phone
        normalized = normalize_phone(value)

        user = self.context.get('request').user
        if User.objects.filter(phone=normalized).exclude(id=user.id).exists():
            raise serializers.ValidationError('Ce numero est deja utilise par un autre compte.')
        return normalized
    

class TokenSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=False)