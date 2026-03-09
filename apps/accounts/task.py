# tasks.py
from celery import shared_task
from .models import SMSLog
from .services.sms import send_sms

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,   # seconds
    autoretry_for=(Exception,),
)
def send_sms_task(self, log_id: str) -> None:
    log = SMSLog.objects.get(id=log_id)
    print("hi")
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


def queue_sms(
    recipient: str,
    message:   str,
    sender_id: str | None = None,
) -> SMSLog:
    """
    Create a log entry and enqueue the task.
    Call this from views, signals, or management commands.
    """
    log = SMSLog.objects.create(
        recipient=recipient,
        message=message,
        sender_id=sender_id or settings.AFRICASTALKING.get("SENDER_ID", ""),
        status=SMSLog.Status.PENDING,
    )
    send_sms_task.delay(str(log.id))
    return log