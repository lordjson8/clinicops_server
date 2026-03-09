from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Optional

import africastalking
from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class SMSRecipientResult:
    number:     str
    status:     str          # "Success" | "InvalidPhoneNumber" | etc.
    message_id: str = ""
    cost:       str = ""
    status_code: int = 0


@dataclass
class SMSSendResult:
    success:    bool
    message:    str = ""
    recipients: list[SMSRecipientResult] = field(default_factory=list)
    raw:        dict = field(default_factory=dict)
    error:      Optional[str] = None


def _get_sms_service():
    """Lazy init — only hits AT once per process."""
    cfg = settings.AFRICASTALKING
    if cfg.get("SANDBOX"):
        africastalking.initialize(cfg["USERNAME"], cfg["API_KEY"], True)
    else:
        africastalking.initialize(cfg["USERNAME"], cfg["API_KEY"])
    return africastalking.SMS


def send_sms(
    message:    str,
    recipients: list[str],          # E.164 format: ["+237XXXXXXXXX"]
    sender_id:  str | None = None,
) -> SMSSendResult:
    """
    Send an SMS via Africa's Talking.
    Returns a structured result — never raises.
    """
    _sender = sender_id or settings.AFRICASTALKING.get("SENDER_ID")

    try:
        sms = _get_sms_service()
        response = sms.send(message, recipients, _sender)
        data = response["SMSMessageData"]

        parsed = [
            SMSRecipientResult(
                number=r["number"],
                status=r["status"],
                message_id=r.get("messageId", ""),
                cost=r.get("cost", ""),
                status_code=r.get("statusCode", 0),
            )
            for r in data.get("Recipients", [])
        ]

        return SMSSendResult(
            success=True,
            message=data.get("Message", ""),
            recipients=parsed,
            raw=response,
        )

    except Exception as exc:
        logger.exception("Africa's Talking SMS error: recipients=%s", recipients)
        return SMSSendResult(success=False, error=str(exc))