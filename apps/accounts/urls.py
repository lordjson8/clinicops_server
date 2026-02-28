from django.urls import path

from .views import (
    LoginView,
    RegisterView,
    LogoutView,
    CheckCookieDeletion,
    RefreshTokenView,
    MeView,
)

app_name = 'accounts'

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('cookie_check/', CheckCookieDeletion.as_view(), name='cookie_check'),
    path('refresh/', RefreshTokenView.as_view(), name='token_refresh'),
    path('me/', MeView.as_view(), name='me'),
]
