from app.models.source import SourceType

PROMPT_VERSION = "extraction_fallback_v1"

_PRICING_SYSTEM_PROMPT = """Extract pricing tiers from this page's visible text. For each tier, capture its
name, price in minor currency units (e.g. cents) and ISO currency code, billing period
(monthly/annual/one_time/unknown), listed features, and whether it is visually highlighted as the
recommended tier. Only extract tiers that are actually present — never invent a tier or a price
that isn't in the text."""

_WEBSITE_SYSTEM_PROMPT = """Extract the page title and a normalized digest of the visible body text
(collapse whitespace). Reflect only what's in the given text — never invent content."""


def system_prompt(source_type: SourceType) -> str:
    return _PRICING_SYSTEM_PROMPT if source_type == SourceType.pricing_page else _WEBSITE_SYSTEM_PROMPT


def build_user_message(page_text: str) -> str:
    return f"Page text:\n{page_text}"
