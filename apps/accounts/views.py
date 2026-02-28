from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.conf import settings
from django.utils import timezone

from .models import User

from .serializers import (
    LoginSerializer,
    UserSerializer,
    RegisterSerializer,
    TokenSerializer,
    UpdateProfileSerializer,
    ClinicRegistrationSerializer,
    AdminRegistrationSerializer,
)

from apps.core.throttling import LoginThrottle, RegisterThrottle, SMSThrottle
from apps.core.utils import normalize_phone, generate_reset_code, send_sms

def _set_refresh_cookie(response, refresh_token, remember_me=False):
    max_age = 30 * 24 * 3600 if remember_me else 7 * 24 * 3600

    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=str(refresh_token),
        max_age=max_age,
        secure=settings.AUTH_COOKIE_SECURE,
        httponly=settings.AUTH_COOKIE_HTTP_ONLY,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        path=settings.AUTH_COOKIE_PATH,
    )

def _delete_refresh_cookie(response):
    response.delete_cookie(
        key=settings.AUTH_COOKIE_NAME,
        path=settings.AUTH_COOKIE_PATH,
    )

def _build_refresh_token(user,remember_me = False):
    refresh = RefreshToken.for_user(user)

    refresh['phone'] = user.phone
    refresh['role'] = user.role
    refresh['clinic_id'] = str(user.clinic.id)
    refresh['full_name'] = user.full_name
    return refresh

class LoginView(GenericAPIView):
    
    """
    Endpoint to authenticate registered user
    """
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]
    serializer_class = LoginSerializer

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
            print("hello")
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
            "refresh_token": str(refresh),
            'user': UserSerializer(user).data,
        })

        _set_refresh_cookie(response, refresh, remember_me)
        return response







class RegisterView(GenericAPIView):
    permission_classes = [AllowAny]
    throttle_classes = [RegisterThrottle]
    serializer_class = RegisterSerializer

    """
    Endpoint to register clinic owner and the clinic
    """

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
                "refresh_token": str(refresh),
                'user': UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )

        _set_refresh_cookie(response, refresh, remember_me=False)
        return response

       



class LogoutView(GenericAPIView):
    """
    Endpoint to logout authenticated users, using refresh token through cookies 
    or refresh token through payload
    {
       "refresh" : "" //optional if cookie given
    } 
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TokenSerializer
    def post(self,request):
        cookie_refresh_token = request.COOKIES.get(settings.AUTH_COOKIE_NAME)
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload_refresh_token = serializer.validated_data.get('refresh', None)

        refresh_token = None
        
        if cookie_refresh_token and payload_refresh_token:
            refresh_token = cookie_refresh_token

        if not cookie_refresh_token and payload_refresh_token:
            refresh_token = payload_refresh_token

        if cookie_refresh_token and not payload_refresh_token:
            refresh_token = cookie_refresh_token


        try:
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except TokenError:
            pass

        response = Response({'message': 'Deconnexion reussie'})
        _delete_refresh_cookie(response)
        return response
    
class CheckCookieDeletion(GenericAPIView):
    permission_classes = [AllowAny]

    """
    Endpoint for testing if cookies where deleted after sucessfull login
    """
    
    def post(self,request):
        try:
            refresh_token = request.COOKIES.get(settings.AUTH_COOKIE_NAME)
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
    permission_classes = [AllowAny]
    serializer_class = TokenSerializer

    """
    Endpoint to refresh tokens, using refresh token through cookies 
    or refresh token through payload
    {
       "refresh" : "" //optional if cookie given
    } 
    """

    def post(self, request):
        cookie_refresh_token = request.COOKIES.get(settings.AUTH_COOKIE_NAME)
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload_refresh_token = serializer.validated_data.get('refresh', None)
       
        if not cookie_refresh_token and not payload_refresh_token:
            return Response(
                {'error': 'no_refresh_token', 'message': 'Session expiree. Veuillez vous reconnecter.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        
        if cookie_refresh_token and payload_refresh_token:
            refresh_token = cookie_refresh_token

        if not cookie_refresh_token and payload_refresh_token:
            refresh_token = payload_refresh_token

        if cookie_refresh_token and not payload_refresh_token:
            refresh_token = cookie_refresh_token

        

        try:
            old_refresh = RefreshToken(refresh_token)
            print(old_refresh)
            access_token = str(old_refresh.access_token)
            new_refresh = str(old_refresh)
            print(new_refresh)
            response = Response({'access_token': access_token, "refresh_token": str(refresh_token)})
            response.set_cookie(
                key=settings.AUTH_COOKIE_NAME,
                value=new_refresh,
                max_age=7 * 24 * 3600,
                secure=settings.AUTH_COOKIE_SECURE,
                httponly=settings.AUTH_COOKIE_HTTP_ONLY,
                samesite=settings.AUTH_COOKIE_SAMESITE,
                path=settings.AUTH_COOKIE_PATH,
            )
            return response

        except TokenError:
            response = Response(
                {'error': 'invalid_token', 'message': 'Session expiree. Veuillez vous reconnecter.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            _delete_refresh_cookie(response)
            return response



class MeView(GenericAPIView):

    permission_classes = [IsAuthenticated]
    serializer_class = UpdateProfileSerializer

    

    def get(self, request):
        return Response(UserSerializer(request.user).data)

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

