from __future__ import annotations

import re

from app.utils.tokens import generate_invite_token

EMAIL_PATTERN = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.IGNORECASE)


def is_valid_email(email: str | None) -> bool:
    return bool(email and EMAIL_PATTERN.match(email.strip()))
def mask_token(token: str | None) -> str:
    if not token:
        return "-"
    if len(token) <= 8:
        return f"{token[:2]}***"
    return f"{token[:4]}***{token[-4:]}"
