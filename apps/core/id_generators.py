from django.utils import timezone

def generate_patient_id(clinic_id):
    """
    Docstring for generate_patient_id
    
    :param clinic_id: the clinic identifier

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
        .value_list('patient_id', flat=True)
        .first()
    )

    seq = int(last.split('-')[-1]) + 1  if last else 1

    return f'{prefix}{seq}:04d'

def generate_visit_id(clinic_id):


    today = timezone.localdate().strftime('Y%m%d')
    prefix = f'VIS-{today}-'

    from apps.visits.models import Visit
    last = (
        Visit.objects
        .filter(clinic_id=clinic_id,visit_id__startswith=prefix)
        .order_by("-visit_id")
        .value_list("visit_id", flat= True)
        .last()
    )

    seq = int(last.split('-')[-1]) + 1 if last else 1
    return f'{prefix}{seq:04d}'


def generate_invoice_number(clinic_id):

    today = timezone.localdate().strftime("%Y%m%d")
    prefix = f'INV-{today}-'

    from apps.billing.models import Invoice

    last = (
        Invoice.objects
        .filter(clinic_id=clinic_id,invoice_id__startswith = prefix)
        .order_by('-invoice_number')
        .value_list('invoice_number', flat= True)
        .last()
    )
    
    seq = int(last.split('-')[-1]) + 1 if last else 1
    return f'{prefix}{seq:04d}'

def generate_payment_id(clinic_id):

    today = timezone.localtime().strftime('%Y%m%d')
    prefix = f'PAY-{today}-'

    from apps.billing.migrations import Payment
    last = (
        Payment.objects
        .filter(clinic_id=clinic_id,payment_id__startswith=prefix)
        .order_by('-payment_id')
        .value_list('payment_id', flat= True)
        .first()    
    )

    seq = int(last.split('-')[-1]) + 1 if last else 1
    return f'{prefix}{seq:04d}'
