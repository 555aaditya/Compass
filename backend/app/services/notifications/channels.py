"""Delivery channels. Credentials come from Settings only and are never logged."""
from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Protocol

import httpx

from app.core.config import Settings


class ChannelError(Exception):
    pass


class Channel(Protocol):
    name: str

    def configured(self) -> bool: ...
    def send(self, subject: str, body: str) -> None: ...


class TelegramChannel:
    name = "telegram"

    def __init__(self, s: Settings, client: httpx.Client | None = None):
        self.s, self.client = s, client or httpx.Client(timeout=15)

    def configured(self) -> bool:
        return bool(self.s.telegram_bot_token and self.s.telegram_chat_id)

    def send(self, subject: str, body: str) -> None:
        url = f"https://api.telegram.org/bot{self.s.telegram_bot_token}/sendMessage"
        try:
            r = self.client.post(url, json={"chat_id": self.s.telegram_chat_id, "text": f"{subject}\n\n{body}"[:4096],
                                            "disable_web_page_preview": True})
        except httpx.HTTPError as exc:
            raise ChannelError(f"telegram network error: {type(exc).__name__}") from None  # no URL: it holds the token
        if r.status_code != 200:
            raise ChannelError(f"telegram HTTP {r.status_code}")


class EmailChannel:
    name = "email"

    def __init__(self, s: Settings, smtp_factory=smtplib.SMTP):
        self.s, self.smtp_factory = s, smtp_factory

    def configured(self) -> bool:
        return bool(self.s.smtp_host and self.s.email_address and self.s.email_password)

    def send(self, subject: str, body: str) -> None:
        msg = EmailMessage()
        msg["Subject"], msg["From"] = subject, self.s.email_address
        msg["To"] = self.s.email_to or self.s.email_address
        msg.set_content(body)
        try:
            with self.smtp_factory(self.s.smtp_host, self.s.smtp_port, timeout=20) as smtp:
                smtp.starttls()
                smtp.login(self.s.email_address, self.s.email_password)
                smtp.send_message(msg)
        except (smtplib.SMTPException, OSError) as exc:
            raise ChannelError(f"email failed: {type(exc).__name__}") from None


class WhatsAppChannel:
    """Official WhatsApp Business Cloud API only. Disabled unless WHATSAPP_ENABLED=true."""
    name = "whatsapp"

    def __init__(self, s: Settings, client: httpx.Client | None = None):
        self.s, self.client = s, client or httpx.Client(timeout=15)

    def configured(self) -> bool:
        return bool(self.s.whatsapp_enabled and self.s.whatsapp_access_token
                    and self.s.whatsapp_phone_number_id and self.s.whatsapp_to)

    def send(self, subject: str, body: str) -> None:
        url = f"https://graph.facebook.com/v20.0/{self.s.whatsapp_phone_number_id}/messages"
        try:
            r = self.client.post(url, headers={"Authorization": f"Bearer {self.s.whatsapp_access_token}"},
                                 json={"messaging_product": "whatsapp", "to": self.s.whatsapp_to, "type": "text",
                                       "text": {"body": f"{subject}\n\n{body}"[:4000]}})
        except httpx.HTTPError as exc:
            raise ChannelError(f"whatsapp network error: {type(exc).__name__}") from None
        if r.status_code >= 300:
            raise ChannelError(f"whatsapp HTTP {r.status_code}")


def build_channels(s: Settings) -> dict[str, Channel]:
    return {c.name: c for c in (TelegramChannel(s), EmailChannel(s), WhatsAppChannel(s))}
