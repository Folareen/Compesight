from pydantic import BaseModel


class LlmCallResult(BaseModel):
    """Typed wrapper around one raw model call — input/output token counts,
    computed cost, and the raw response text, before any schema validation
    of that text happens. Keeps the untyped API response from traveling
    past the call site."""

    input_tokens: int
    output_tokens: int
    cost_cents: int
    raw_text: str
