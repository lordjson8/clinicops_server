from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone

from apps.core.id_generators import generate_invoice_number, generate_payment_id
from .models import Invoice, InvoiceLine, Payment


@transaction.atomic
def create_invoice_from_visit(visit, created_by, discount_percent=0, discount_amount=0, discount_reason=''):
    """
    Generate an invoice from a visit's services.
    Sets visit status to 'invoiced'.
    """
    if visit.status != 'open':
        raise ValueError(f"Impossible de facturer une visite avec le statut \"{visit.status}\".")

    visit_services = visit.services.select_related('service').all()
    if not visit_services.exists():
        raise ValueError("La visite doit avoir au moins un service pour generer une facture.")

    subtotal = sum(vs.line_total for vs in visit_services)

    # Apply discount
    if discount_percent > 0:
        calc_discount = int(subtotal * discount_percent / 100)
    elif discount_amount > 0:
        calc_discount = discount_amount
    else:
        calc_discount = 0

    calc_discount = min(calc_discount, subtotal)
    total = subtotal - calc_discount

    invoice = Invoice.objects.create(
        invoice_number=generate_invoice_number(visit.clinic_id),
        visit=visit,
        patient=visit.patient,
        clinic=visit.clinic,
        subtotal=subtotal,
        discount_percent=discount_percent,
        discount_amount=calc_discount,
        discount_reason=discount_reason,
        total=total,
        paid_amount=0,
        balance=total,
        status='pending',
        created_by=created_by,
    )

    for vs in visit_services:
        price = vs.price_override if vs.price_override is not None else vs.unit_price
        InvoiceLine.objects.create(
            invoice=invoice,
            visit_service=vs,
            name=vs.service.name,
            quantity=vs.quantity,
            unit_price=price,
            total=vs.line_total,
        )

    visit.status = 'invoiced'
    visit.save(update_fields=['status', 'updated_at'])

    return invoice


@transaction.atomic
def record_payment(invoice, amount, payment_method, received_by, reference_number='', notes=''):
    """Record a payment against an invoice. Auto-updates invoice status."""
    if invoice.status in ('paid', 'cancelled'):
        raise ValueError(f"Impossible d'enregistrer un paiement sur une facture \"{invoice.status}\".")

    if amount <= 0:
        raise ValueError("Le montant doit etre positif.")

    if amount > invoice.balance:
        raise ValueError(
            f"Le montant ({amount} XAF) depasse le solde restant ({invoice.balance} XAF)."
        )

    if payment_method == 'bank_transfer' and not reference_number:
        raise ValueError("Le numero de reference est requis pour un virement bancaire.")

    payment = Payment.objects.create(
        payment_id=generate_payment_id(invoice.clinic_id),
        invoice=invoice,
        clinic=invoice.clinic,
        amount=amount,
        payment_method=payment_method,
        reference_number=reference_number,
        payment_date=timezone.now(),
        notes=notes,
        received_by=received_by,
    )

    invoice.paid_amount += amount
    invoice.balance = invoice.total - invoice.paid_amount

    if invoice.balance == 0:
        invoice.status = 'paid'
        # Mark the visit as completed
        visit = invoice.visit
        visit.status = 'completed'
        visit.save(update_fields=['status', 'updated_at'])
    elif invoice.paid_amount > 0:
        invoice.status = 'partial'

    invoice.save(update_fields=['paid_amount', 'balance', 'status', 'updated_at'])

    return payment


@transaction.atomic
def void_invoice(invoice, voided_by, reason):
    """Void an invoice. Only allowed if no confirmed payments."""
    if invoice.status == 'cancelled':
        raise ValueError("Cette facture est deja annulee.")

    confirmed_payments = invoice.payments.filter(status='confirmed').aggregate(
        total=Sum('amount')
    )['total'] or 0

    if confirmed_payments > 0:
        raise ValueError(
            "Impossible d'annuler une facture avec des paiements confirmes. "
            "Annulez d'abord les paiements."
        )

    invoice.status = 'cancelled'
    invoice.voided_at = timezone.now()
    invoice.voided_by = voided_by
    invoice.void_reason = reason
    invoice.save(update_fields=['status', 'voided_at', 'voided_by', 'void_reason', 'updated_at'])

    # Revert visit status to open for re-invoicing
    visit = invoice.visit
    visit.status = 'open'
    visit.save(update_fields=['status', 'updated_at'])

    return invoice


@transaction.atomic
def void_payment(payment, voided_by, reason):
    """Void a payment and recalculate invoice totals."""
    if payment.status == 'voided':
        raise ValueError("Ce paiement est deja annule.")

    payment.status = 'voided'
    payment.voided_at = timezone.now()
    payment.voided_by = voided_by
    payment.void_reason = reason
    payment.save(update_fields=['status', 'voided_at', 'voided_by', 'void_reason', 'updated_at'])

    # Recalculate invoice from confirmed payments
    invoice = payment.invoice
    confirmed_total = invoice.payments.filter(status='confirmed').aggregate(
        total=Sum('amount')
    )['total'] or 0

    invoice.paid_amount = confirmed_total
    invoice.balance = invoice.total - confirmed_total

    if confirmed_total == 0:
        invoice.status = 'pending'
    elif confirmed_total < invoice.total:
        invoice.status = 'partial'
    else:
        invoice.status = 'paid'

    invoice.save(update_fields=['paid_amount', 'balance', 'status', 'updated_at'])

    # If invoice is no longer paid, revert visit from completed
    if invoice.status != 'paid':
        visit = invoice.visit
        if visit.status == 'completed':
            visit.status = 'invoiced'
            visit.save(update_fields=['status', 'updated_at'])

    return payment
