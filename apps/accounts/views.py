from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.conf import settings
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers,vary_on_cookie

from drf_spectacular.utils import (
extend_schema,
OpenApiParameter,
OpenApiExample,
OpenApiResponse,
inline_serializer,
PolymorphicProxySerializer,
)
from drf_spectacular.types import OpenApiTypes



from .models import User

from .serializers import (
    LoginSerializer,
    UserSerializer,
    RegisterSerializer,
    TokenSerializer,
    UpdateProfileSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    ChangePasswordSerializer
)

from apps.core.throttling import LoginThrottle, RegisterThrottle, SMSThrottle
from apps.core.utils import normalize_phone, generate_reset_code
from .task import queue_sms
from .services.token import _build_refresh_token,_delete_refresh_cookie, _set_refresh_cookie

class LoginView(GenericAPIView):
    
    """
    Endpoint to authenticate registered user
    """
    permission_classes = [AllowAny]
    # throttle_classes = [LoginThrottle]
    serializer_class = LoginSerializer

    @extend_schema(
        tags=['Authentication'], summary='Authenticate user', auth=[],
        request=LoginSerializer,
        responses={
        200: OpenApiResponse(description='Login Successful',examples=[
        OpenApiExample('Success', value={
        'access_token': 'token here',
        'user': '',
        })
        ]),
        400: OpenApiResponse(description='Validation error',
        response=LoginSerializer),
        },
    )
    def post(self,request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        phone = normalize_phone(validated_data['phone'])
        password = validated_data['password']
        remember_me = validated_data['remember_me']

        try:
            user = User.objects.get(phone=phone)
            
        except User.DoesNotExist:
            return Response(
                {
                    'error': "invalid_credentials", 
                    'message': 'Numero de telephone ou mot de passe incorrect',
                },
                status=status.HTTP_401_UNAUTHORIZED
            )

        if user.is_locked:
            remaining = max(1,(user.locked_until - timezone.now()).seconds // 60)
            return Response(
                {
                    'error': "account_locked", 
                    'message': f'Compte bloque. Reessayez dans {remaining} minutes.',
                    'lockedUntil': user.locked_until.isoformat(),
                },
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if not user.is_active:
            return Response(
                {'error': 'account_disabled', 'message': 'Ce compte a ete desactive.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        
        if not user.check_password(password):
            user.increment_failed_attempts()
            return Response(
                {'error': 'invalid_credentials', 'message': 'Numero de telephone ou mot de passe incorrect'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        
        user.reset_failed_attempts()
        user.last_login = timezone.now()
        user.last_login_ip = request.META.get('REMOTE_ADDR')
        user.save(update_fields=['last_login', 'last_login_ip', 'failed_login_attempts', 'locked_until'])

        # 6. Generate tokens
        refresh = _build_refresh_token(user)

        response = Response({
            'access_token': str(refresh.access_token),
            'user': UserSerializer(user).data,
        })

        _set_refresh_cookie(response, refresh, user.role, remember_me)
        return response







class RegisterView(GenericAPIView):
    """Register a new clinic owner and their clinic."""
    permission_classes = [AllowAny]
    throttle_classes = [RegisterThrottle]
    serializer_class = RegisterSerializer

    @extend_schema(
        tags=['Authentication'], summary='Register clinic & owner', auth=[],
        request=RegisterSerializer,
        responses={201: OpenApiResponse(description='Registration successful')},
    )
    def post(self,request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        clinic_data = validated_data['clinic']
        admin_data = validated_data['admin']
        print(admin_data,clinic_data)

        from apps.clinics.models import Clinic
        clinic = Clinic.objects.create(
            name=clinic_data['name'],
            address=clinic_data.get('address', ''),
            phone_primary= clinic_data['phone'],
            email=clinic_data.get('email', ''),
        )



        user = User.objects.create_user(
            phone=admin_data['phone'],
            first_name=admin_data['firstName'],
            last_name=admin_data['lastName'],
            email=admin_data.get('email', ''),
            password=admin_data['password'],
            role='owner',
            clinic=clinic,
            must_change_password=False,
        )

        refresh = _build_refresh_token(user)

        response = Response(
            {
                'message': 'Inscription reussie',
                'access_token': str(refresh.access_token),
                'user': UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )

        _set_refresh_cookie(response, refresh, user.role, remember_me=False)
        return response

       



class LogoutView(GenericAPIView):
    """Logout and blacklist the refresh token."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Authentication'], summary='Logout', request=None,
        responses={200: OpenApiResponse(description='Logged out successfully')},
    )
    def post(self,request):
        refresh_token = request.COOKIES.get(settings.AUTH_COOKIE_NAME)
        
        try:
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except TokenError:
            pass

        response = Response({'message': 'Deconnexion reussie'})
        _delete_refresh_cookie(response)
        return response
    

    
@extend_schema(exclude=True)
class CheckCookieDeletion(APIView):
    """Internal test helper — hidden from docs."""
    permission_classes = [AllowAny]

    def post(self,request):
        try:
            refresh_token = request.COOKIES.get(settings.AUTH_COOKIE_NAME)
            print(refresh_token)
            if refresh_token:
                print(refresh_token)
                return Response({
                    "status": "cookie present"
                })
        except TokenError:
            pass

        return Response({
                "status": "cookie absent"
            })



class RefreshTokenView(GenericAPIView):
    """Refresh access token using the refresh cookie."""
    permission_classes = [AllowAny]
    serializer_class = TokenSerializer

    @extend_schema(
        tags=['Authentication'], summary='Refresh access token', auth=[],
        responses={200: OpenApiResponse(description='New access token')},
    )
    def post(self, request):

        refresh_token = request.COOKIES.get(settings.AUTH_COOKIE_NAME)
        
        if not refresh_token:
            return Response(
                {'error': 'no_refresh_token', 'message': 'Session expiree. Veuillez vous reconnecter.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        

        try:
            old_refresh = RefreshToken(refresh_token)
            role = old_refresh.get("role")
            new_refresh = str(old_refresh)
            access_token = str(old_refresh.access_token)
            response = Response({'access_token': access_token})
            
            response.set_cookie(
                key=settings.AUTH_COOKIE_NAME,
                value=new_refresh,
                max_age=7 * 24 * 3600,
                secure=settings.AUTH_COOKIE_SECURE,
                httponly=settings.AUTH_COOKIE_HTTP_ONLY,
                samesite=settings.AUTH_COOKIE_SAMESITE,
                path=settings.AUTH_COOKIE_PATH,
            )

            response.set_cookie(
                key=settings.ROLE_COOKIE_NAME,
                value=role,
                max_age=7 * 24 * 3600,
                secure=settings.ROLE_COOKIE_SECURE,
                httponly=settings.ROLE_COOKIE_HTTP_ONLY,
                samesite=settings.ROLE_COOKIE_SAMESITE,
            )

            return response

        except TokenError:
            response = Response(
                {'error': 'invalid_token', 'message': 'Session expiree. Veuillez vous reconnecter.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            _delete_refresh_cookie(response)
            return response

class PasswordResetRequestView(GenericAPIView):
    """Request a password reset code via SMS."""
    permission_classes = [AllowAny]
    throttle_scope = 'sms'
    serializer_class = PasswordResetRequestSerializer

    @extend_schema(
        tags=['Authentication'], summary='Request password reset code', auth=[],
        request=PasswordResetRequestSerializer,
        responses={200: OpenApiResponse(description='Code sent if phone exists')},
    )
    def post(self,request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = normalize_phone(serializer.validated_data['phone'])

        try:

            user = User.objects.get(phone=phone)
            code = generate_reset_code()
            user.set_reset_code(code)

            print(f"[SMS → {user.phone}] {code}")
            queue_sms(
                    recipient=user.phone,
                    message=f"Votre code de verification ClinicOps: {code}. Valide 15 minutes.",
                    sender_id= "ClinicOps Verification Code"
                )

        except User.DoesNotExist:
            pass

        return Response({
            'message': 'Si ce numero existe, un code de verification a ete envoye',
            'validity_minutes': 15
        })
    
class PasswordResetConfirmView(GenericAPIView):
    """Confirm password reset with the SMS code."""
    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    @extend_schema(
        tags=['Authentication'], summary='Confirm password reset', auth=[],
        request=PasswordResetConfirmSerializer,
        responses={200: OpenApiResponse(description='Password changed')},
    )
    def post(self,request):

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        phone = normalize_phone(validated_data['phone'])
        password = validated_data['password']
        code = validated_data['code']

        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist: 
            return Response(
                {'error': 'invalid_code', 'message': 'Code invalide ou expire'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        print(user.reset_attempts_locked, user.reset_attempts_locked_until)
        if user.reset_attempts_locked:
            remaining = max(1,(user.reset_attempts_locked_until - timezone.now()).seconds // 60)
            return Response(
                {
                    'error': "reset_attempts_locked", 
                    'message': f'Trop de tentative. Reessayez dans {remaining} minutes.',
                    'lockedUntil': user.reset_attempts_locked_until.isoformat(),
                },
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if not user.verify_reset_code(code):
            user.increment_failed_reset_attempts()
            return Response(
                {'error': 'invalid_code', 'message': 'Code invalide ou expire'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(password)
        user.clear_reset_code()

        return Response({'message': 'Mot de passe modifie avec succes'})

class ChangePasswordView(GenericAPIView):
    """Change password for the authenticated user."""
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    @extend_schema(
        tags=['Authentication'], summary='Change password',
        request=ChangePasswordSerializer,
        responses={200: OpenApiResponse(description='Password changed')},
    )
    def post(self,request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        current_password = serializer.validated_data['currentPassword']
        new_password = serializer.validated_data['newPassword']

        user = request.user

        if not user.check_password(current_password):
            return Response(
                {'error': 'invalid_password', 'message': 'Mot de passe actuel incorrect'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.must_change_password = False
        user.password_changed_at = timezone.now()
        user.save()

        return Response({'message': 'Mot de passe modifie avec succes'})


class MeView(GenericAPIView):
    """Get or update the current user's profile."""
    permission_classes = [IsAuthenticated]
    serializer_class = UpdateProfileSerializer

    @extend_schema(tags=['Settings'], summary='Get current user profile', responses={200: UserSerializer})
    @method_decorator(cache_page(60 * 15, key_prefix="current_user"))
    @method_decorator(vary_on_headers("Authorization"))
    def get(self, request):
        return Response(UserSerializer(request.user).data)

    @extend_schema(tags=['Settings'], summary='Update current user profile', request=UpdateProfileSerializer, responses={200: UserSerializer})
    def patch(self, request):
        serializer = UpdateProfileSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)

        user = request.user
        data = serializer.validated_data

        if 'firstName' in data:
            user.first_name = data['firstName']
        if 'lastName' in data:
            user.last_name = data['lastName']
        if 'phone' in data:
            user.phone = data['phone']
        if 'email' in data:
            user.email = data['email']

        user.save()
        return Response(UserSerializer(user).data)

