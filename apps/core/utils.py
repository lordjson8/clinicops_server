import re
import random
import string
import logging

logger = logging.getLogger(__name__)


def normalize_phone(phone):
    """
    Normalize a Cameroon phone number to +237XXXXXXXXX format.
    Strips spaces, dashes, dots, and handles common input patterns:
      - "699 123 456"       → "+237699123456"
      - "+237 699 123 456"  → "+237699123456"
      - "237699123456"      → "+237699123456"
      - "699123456"         → "+237699123456"
    """
    if not phone:
        return ''

    # Remove all non-digit chars except leading +
    cleaned = re.sub(r'[^\d+]', '', phone)

    # Remove leading + for processing
    if cleaned.startswith('+'):
        cleaned = cleaned[1:]

    # If starts with 237 and has 12 digits total, it's already full
    if cleaned.startswith('237') and len(cleaned) == 12:
        return f'+{cleaned}'

    # If 9 digits starting with 6, it's a local number
    if len(cleaned) == 9 and cleaned.startswith('6'):
        return f'+237{cleaned}'

    # If 12 digits starting with 237
    if len(cleaned) == 12 and cleaned.startswith('237'):
        return f'+{cleaned}'

    # Fallback: return as-is with +
    return f'+{cleaned}' if not phone.startswith('+') else phone


def generate_temp_password(length=10):
    """
    Generate a temporary password for staff invitations.
    Contains at least 1 uppercase, 1 lowercase, 1 digit.
    """
    chars = string.ascii_letters + string.digits
    while True:
        password = ''.join(random.choices(chars, k=length))
        if (any(c.isupper() for c in password)
                and any(c.islower() for c in password)
                and any(c.isdigit() for c in password)):
            return password


def generate_reset_code():
    """Generate a 6-digit numeric reset code."""
    return str(random.randint(100000, 999999))

