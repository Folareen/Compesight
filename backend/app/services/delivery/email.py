import httpx

from app.config import settings
from app.services.delivery.base import AlertMessage, DeliveryFailed

_RESEND_API_URL = "https://api.resend.com/emails"


async def _send_email(recipient_email: str, subject: str, body: str) -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(
                _RESEND_API_URL,
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={
                    "from": settings.alert_from_email,
                    "to": [recipient_email],
                    "subject": subject,
                    "text": body,
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise DeliveryFailed(str(exc)) from exc


async def send_via_resend(recipient_email: str, message: AlertMessage) -> None:
    subject = f"[{message.urgency.upper()}] {message.title}"
    body = (
        f"{message.competitor_name} — {message.change_type}\n\n"
        f"{message.summary}\n\n"
        f"View details: {message.detail_url}"
    )
    await _send_email(recipient_email, subject, body)


async def send_digest_via_resend(recipient_email: str, period_label: str, messages: list[AlertMessage]) -> None:
    lines = [f"{m.competitor_name} — [{m.urgency.upper()}] {m.title}\n{m.summary}\n{m.detail_url}" for m in messages]
    subject = f"Compesight weekly digest — {period_label} ({len(messages)} changes)"
    body = "\n\n".join(lines)
    await _send_email(recipient_email, subject, body)
