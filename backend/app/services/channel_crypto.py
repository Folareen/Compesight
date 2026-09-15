import json

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings
from app.schemas.notification_channel import (
    ChannelConfig,
    EmailChannelConfig,
    SlackChannelConfig,
    WebhookChannelConfig,
)

_KIND_TO_MODEL = {
    "email": EmailChannelConfig,
    "slack": SlackChannelConfig,
    "webhook": WebhookChannelConfig,
}


class ChannelConfigDecryptionError(Exception):
    pass


def _fernet() -> Fernet:
    return Fernet(settings.channel_encryption_key.encode())


def encrypt_channel_config(config: ChannelConfig) -> dict:
    """Encrypts the whole config blob at rest — it holds a Slack webhook
    URL, a generic webhook secret, or a recipient email
    (docs/data-model.md: "Webhook secrets and Slack tokens live here —
    encrypted at rest, never logged"). Stored as a single opaque field
    inside the jsonb column rather than per-field, since the whole thing
    is secret-adjacent."""
    plaintext = config.model_dump_json().encode()
    token = _fernet().encrypt(plaintext)
    return {"kind": config.kind.value, "ciphertext": token.decode()}


def decrypt_channel_config(stored: dict) -> ChannelConfig:
    try:
        plaintext = _fernet().decrypt(stored["ciphertext"].encode())
    except InvalidToken as exc:
        raise ChannelConfigDecryptionError("channel config could not be decrypted") from exc

    model = _KIND_TO_MODEL[stored["kind"]]
    return model.model_validate(json.loads(plaintext))
