from django.contrib import admin

from .models import Clinic, Service


@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'phone_primary', 'is_active', 'created_at')
    search_fields = ('name', 'city', 'phone_primary')
    list_filter = ('is_active', 'region')


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'category', 'price', 'clinic', 'is_active')
    search_fields = ('name', 'code')
    list_filter = ('category', 'is_active', 'clinic')
