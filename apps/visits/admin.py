from django.contrib import admin

from .models import Visit, VisitService


class VisitServiceInline(admin.TabularInline):
    model = VisitService
    extra = 0
    readonly_fields = ('unit_price', 'line_total')


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ('visit_id', 'patient', 'visit_type', 'status', 'clinic', 'created_at')
    list_filter = ('status', 'visit_type', 'clinic')
    search_fields = ('visit_id', 'patient__first_name', 'patient__last_name')
    inlines = [VisitServiceInline]


@admin.register(VisitService)
class VisitServiceAdmin(admin.ModelAdmin):
    list_display = ('visit', 'service', 'quantity', 'unit_price', 'price_override', 'line_total')
