from __future__ import annotations

import secrets
import string
from datetime import datetime

ALPHA_NUM = string.ascii_uppercase + string.digits


def _random_code(length: int = 6) -> str:
    return "".join(secrets.choice(ALPHA_NUM) for _ in range(length))


def generate_numero_billet() -> str:
    """Format TRV-AAAA-XXXXXX (ex: TRV-2026-AX42K9)."""
    return f"TRV-{datetime.now().year}-{_random_code(6)}"


def generate_numero_reclamation() -> str:
    """Format REC-AAAA-NNNN (ex: REC-2026-0042)."""
    return f"REC-{datetime.now().year}-{_random_code(4)}"
