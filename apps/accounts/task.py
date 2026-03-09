from celery import shared_task
import logging
from .models import User
from .models import SMSLog



logger = logging.getLogger(__name__)

@shared_task
def send_sms(to, message):
    """
    Send an SMS message.

    TODO: Replace with your SMS provider integration.
    Options for Cameroon:
      - Africa's Talking
      - Twilio
      - Nexmo/Vonage
      - Local providers

    For development, this just logs the message.
    """
    logger.info(f"[SMS → {to}] {message}")
    print(f"[SMS → {to}] {message}")
    
    # ---- PRODUCTION: uncomment your provider ----

    # --- Africa's Talking ---
    # import africastalking
    # africastalking.initialize(username='your_username', api_key='your_api_key')
    # sms = africastalking.SMS
    # sms.send(message, [to])

    # --- Twilio ---
    # from twilio.rest import Client
    # from django.conf import settings
    # client = Client(settings.TWILIO_SID, settings.TWILIO_AUTH_TOKEN)
    # client.messages.create(body=message, from_=settings.TWILIO_FROM, to=to)

    return True


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,   # seconds
    autoretry_for=(Exception,),
)
def send_sms_task(self, log_id: str) -> None:
    log = SMSLog.objects.get(id=log_id)

    result = send_sms(
        message=log.message,
        recipients=[log.recipient],
        sender_id=log.sender_id or None,
    )

    if result.success and result.recipients:
        r = result.recipients[0]
        log.status = (
            SMSLog.Status.SENT if r.status == "Success"
            else SMSLog.Status.REJECTED
        )
        log.at_message_id = r.message_id
        log.cost = r.cost
        log.failure_reason = "" if r.status == "Success" else r.status
    else:
        log.status = SMSLog.Status.FAILED
        log.failure_reason = result.error or "Unknown error"

    log.save(update_fields=["status", "at_message_id", "cost", "failure_reason", "updated_at"])