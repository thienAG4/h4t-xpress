"""OTP delivery. The demo sender keeps the code so the API can show it (no real SMS, D11).

A real SMS provider only needs another class with the same `send` method.
"""

import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class OtpSender(Protocol):
    def send(self, phone: str, code: str) -> None: ...


class DemoOtpSender:
    def send(self, phone: str, code: str) -> None:
        logger.info(
            "[DemoOtpSender] OTP for %s***%s generated (shown on screen)", phone[:4], phone[-2:]
        )


otp_sender: OtpSender = DemoOtpSender()


def mask_phone(phone: str | None) -> str:
    if not phone:
        return ""
    return f"{phone[:4]}****{phone[-2:]}"
