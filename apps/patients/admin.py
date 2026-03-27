from django.contrib import admin
from .models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    # list_display = ["patient_id", "name", "phone", "gender", "outstanding_balance", "created_at"]
    search_fields = ["patient_id", "name", "phone"]
    list_filter = ["gender", "created_at"]
    readonly_fields = ["id", "patient_id", "created_at", "updated_at"]
    ordering = ["-created_at"]
