from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

def _set_refresh_cookie(response, refresh_token,role, remember_me=False):
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

    response.set_cookie(
        key=settings.ROLE_COOKIE_NAME,
        value=role,
        max_age=max_age,
        secure=settings.ROLE_COOKIE_SECURE,
        httponly=settings.ROLE_COOKIE_HTTP_ONLY,
        samesite=settings.ROLE_COOKIE_SAMESITE,
    )



def _delete_refresh_cookie(response):
    response.delete_cookie(
        key=settings.AUTH_COOKIE_NAME,
        path=settings.AUTH_COOKIE_PATH,
    )

    response.delete_cookie(
        key=settings.ROLE_COOKIE_NAME,
        # path=settings.ROLE_COOKIE_PATH,
    )

def _build_refresh_token(user,remember_me = False):
    refresh = RefreshToken.for_user(user)

    refresh['phone'] = user.phone
    refresh['role'] = user.role
    refresh['clinic_id'] = str(user.clinic.id)
    refresh['full_name'] = user.full_name
    return refresh