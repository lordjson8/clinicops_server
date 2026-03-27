from django.contrib import admin

from .models import Invoice, InvoiceLine, Payment


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0
    readonly_fields = ('name', 'quantity', 'unit_price', 'total')


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ('payment_id', 'amount', 'payment_method', 'received_by')


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'patient', 'total', 'paid_amount', 'balance', 'status', 'clinic')
    list_filter = ('status', 'clinic')
    search_fields = ('invoice_number', 'patient__first_name', 'patient__last_name')
    inlines = [InvoiceLineInline, PaymentInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_id', 'invoice', 'amount', 'payment_method', 'status', 'received_by')
    list_filter = ('payment_method', 'status', 'clinic')
    search_fields = ('payment_id', 'invoice__invoice_number')
