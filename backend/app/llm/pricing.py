"""Per-model $/token rates for llm_usage.cost_cents. A lookup, not a
fetched value — update when Settings' model IDs change. Source: the
claude-api skill's pricing table."""

_CENTS_PER_MILLION_INPUT = {
    "claude-haiku-4-5": 100,
    "claude-sonnet-5": 200,
}
_CENTS_PER_MILLION_OUTPUT = {
    "claude-haiku-4-5": 500,
    "claude-sonnet-5": 1_000,
}


def cost_cents(model: str, input_tokens: int, output_tokens: int) -> int:
    input_rate = _CENTS_PER_MILLION_INPUT[model]
    output_rate = _CENTS_PER_MILLION_OUTPUT[model]
    input_cost = (input_tokens * input_rate) / 1_000_000
    output_cost = (output_tokens * output_rate) / 1_000_000
    return round(input_cost + output_cost)
