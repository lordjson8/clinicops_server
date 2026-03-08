from celery import shared_task
import logging
from .models import User

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