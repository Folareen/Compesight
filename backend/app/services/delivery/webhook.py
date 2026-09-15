import hashlib
import hmac
import json

import httpx

from app.services.delivery.base import AlertMessage, DeliveryFailed


def _signature(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


async def send_via_generic_webhook(url: str, secret: str | None, message: AlertMessage) -> None:
    payload = {
        "competitor_name": message.competitor_name,
        "title": message.title,
        "summary": message.summary,
        "urgency": message.urgency,
        "change_type": message.change_type,
        "detail_url": message.detail_url,
    }
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if secret is not None:
        headers["X-Compesight-Signature"] = _signature(secret, body)

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(url, content=body, headers=headers)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise DeliveryFailed(str(exc)) from exc
