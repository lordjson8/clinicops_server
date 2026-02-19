from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken


class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication:
    1. Check Authorization header for access token
    2. Validate and return user
    3. If no header, return None (unauthenticated — let the refresh endpoint handle it)

    Does NOT read the refresh token from the cookie here.
    The RefreshTokenView reads the cookie directly.
    """

    def authenticate(self, request):
        header = self.get_header(request)
        if header is not None:
            raw_token = self.get_raw_token(header)
            if raw_token is not None:
                validated_token = self.get_validated_token(raw_token)
                return self.get_user(validated_token), validated_token
        return None

    def get_user(self, validated_token):
        user = super().get_user(validated_token)

        if not user.is_active:
            raise InvalidToken('Ce compte a ete desactive.')

        if user.is_locked:
            raise InvalidToken('Ce compte est temporairement bloque.')

        return user