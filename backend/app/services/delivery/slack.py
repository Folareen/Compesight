import httpx

from app.services.delivery.base import AlertMessage, DeliveryFailed


async def send_via_slack_webhook(webhook_url: str, message: AlertMessage) -> None:
    text = (
        f"*[{message.urgency.upper()}] {message.title}*\n"
        f"{message.competitor_name} — {message.change_type}\n"
        f"{message.summary}\n"
        f"<{message.detail_url}|View details>"
    )
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(webhook_url, json={"text": text})
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise DeliveryFailed(str(exc)) from exc


async def send_verification_ping(webhook_url: str) -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(
                webhook_url, json={"text": "Compesight is now connected to this channel."}
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise DeliveryFailed(str(exc)) from exc
