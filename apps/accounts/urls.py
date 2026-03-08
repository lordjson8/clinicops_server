from django.urls import path

from .views import (
    LoginView,
    RegisterView,
    LogoutView,
    CheckCookieDeletion,
    RefreshTokenView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    ChangePasswordView
)

app_name = 'accounts'

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('cookie_check/', CheckCookieDeletion.as_view(), name='cookie_check'),
    path('refresh/', RefreshTokenView.as_view(), name='token_refresh'),
    path('me/', MeView.as_view(), name='me'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password_reset'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
]
