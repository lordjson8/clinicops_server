"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from django.conf import settings


def health_check(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    # Health check — Railway hits this to know your app is alive
    path('health/', health_check, name='health-check'),

    # path('admin/', admin.site.urls),

    # API v1
    path('api/v1/auth/', include('apps.accounts.urls')),
    path('api/v1/clinic/', include('apps.clinics.urls')),
    path('api/v1/services/', include('apps.clinics.service_urls')),
    path('api/v1/staff/', include('apps.accounts.staff_urls')),
    path('api/v1/patients/', include('apps.patients.urls')),
    path('api/v1/visits/', include('apps.visits.urls')),
    path('api/v1/invoices/', include('apps.billing.invoice_urls')),
    path('api/v1/payments/', include('apps.billing.payment_urls')),
    path('api/v1/reconciliation/', include('apps.billing.reconciliation_urls')),
    path('api/v1/reports/', include('apps.reports.urls')),
    path('api/v1/audit/', include('apps.audit.urls')),
]

if settings.DEBUG:
    urlpatterns += [
        path('admin/', admin.site.urls),
        # YOUR PATTERNS
        path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
        # Optional UI:
        path('', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
        path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
        path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    ]