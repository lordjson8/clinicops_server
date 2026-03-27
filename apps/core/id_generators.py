from django.utils import timezone


def generate_patient_id(clinic_id):
    """
    Generate: PAT-YYYYMMDD-XXXX
    Scoped per clinic, per day. Sequence resets daily.
    Uses all_objects to include soft-deleted records in numbering.
    """
    today = timezone.localdate().strftime('%Y%m%d')
    prefix = f'PAT-{today}-'

    from apps.patients.models import Patient
    last = (
        Patient.all_objects
        .filter(clinic_id=clinic_id, patient_id__startswith=prefix)
        .order_by('-patient_id')
        .values_list('patient_id', flat=True)
        .first()
    )

    seq = int(last.split('-')[-1]) + 1 if last else 1
    return f'{prefix}{seq:04d}'


def generate_visit_id(clinic_id):
    """
    Generate: VIS-YYYYMMDD-XXXX
    Scoped per clinic, per day. Sequence resets daily.
    """
    today = timezone.localdate().strftime('%Y%m%d')
    prefix = f'VIS-{today}-'

    from apps.visits.models import Visit
    last = (
        Visit.objects
        .filter(clinic_id=clinic_id, visit_id__startswith=prefix)
        .order_by('-visit_id')
        .values_list('visit_id', flat=True)
        .first()
    )

    seq = int(last.split('-')[-1]) + 1 if last else 1
    return f'{prefix}{seq:04d}'


def generate_invoice_number(clinic_id):
    """
    Generate: INV-YYYYMM-XXXX
    Scoped per clinic, per month. Sequence resets monthly.
    """
    today = timezone.localdate().strftime('%Y%m')
    prefix = f'INV-{today}-'

    from apps.billing.models import Invoice
    last = (
        Invoice.objects
        .filter(clinic_id=clinic_id, invoice_number__startswith=prefix)
        .order_by('-invoice_number')
        .values_list('invoice_number', flat=True)
        .first()
    )

    seq = int(last.split('-')[-1]) + 1 if last else 1
    return f'{prefix}{seq:04d}'


def generate_payment_id(clinic_id):
    """
    Generate: PAY-YYYYMMDD-XXXX
    Scoped per clinic, per day. Sequence resets daily.
    """
    today = timezone.localdate().strftime('%Y%m%d')
    prefix = f'PAY-{today}-'

    from apps.billing.models import Payment
    last = (
        Payment.objects
        .filter(clinic_id=clinic_id, payment_id__startswith=prefix)
        .order_by('-payment_id')
        .values_list('payment_id', flat=True)
        .first()
    )

    seq = int(last.split('-')[-1]) + 1 if last else 1
    return f'{prefix}{seq:04d}'
