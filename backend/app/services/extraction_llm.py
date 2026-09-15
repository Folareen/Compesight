import json
import uuid

import anthropic
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.llm.client import get_client
from app.llm.pricing import cost_cents
from app.llm.prompts.extraction_fallback_v1 import build_user_message, system_prompt
from app.models.llm_usage import LlmPurpose
from app.models.source import SourceType
from app.repositories import llm_usage as llm_usage_repo
from app.repositories import workspaces as workspaces_repo
from app.schemas.extraction_fields import ExtractionFields, PricingPageFields, WebsitePageFields
from app.services.llm_budget import BudgetStatus, check_budget

_MAX_RETRIES = 1


def _schema_for(source_type: SourceType) -> tuple[type[PricingPageFields] | type[WebsitePageFields], dict]:
    model = PricingPageFields if source_type == SourceType.pricing_page else WebsitePageFields
    schema = model.model_json_schema()
    schema["additionalProperties"] = False
    return model, schema


async def _call_model(
    client: anthropic.AsyncAnthropic, source_type: SourceType, user_message: str, schema: dict
) -> tuple[str, int, int]:
    response = await client.messages.create(
        model=settings.llm_extraction_fallback_model,
        max_tokens=4096,
        system=system_prompt(source_type),
        output_config={"format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": user_message}],
    )
    text = next(block.text for block in response.content if block.type == "text")
    return text, response.usage.input_tokens, response.usage.output_tokens


async def extract_with_llm(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    source_type: SourceType,
    page_text: str,
) -> ExtractionFields | None:
    """LLM extraction fallback for pages selectors can't handle
    (docs/llm-usage.md). Fixed schema per source type so the result stays
    diffable at the field level. Returns None on budget exhaustion or
    repeated malformed output — the caller keeps its existing
    ExtractionFailed/degraded handling in that case, this is additive."""
    workspace = await workspaces_repo.get_by_id(db, workspace_id)
    if workspace is None:
        return None

    if await check_budget(db, workspace) == BudgetStatus.hard_stop:
        return None

    model_cls, schema = _schema_for(source_type)
    user_message = build_user_message(page_text[: settings.llm_max_input_chars])

    client = get_client()
    for _attempt in range(_MAX_RETRIES + 1):
        text, input_tokens, output_tokens = await _call_model(client, source_type, user_message, schema)
        await llm_usage_repo.create(
            db,
            workspace_id,
            LlmPurpose.extraction_fallback,
            settings.llm_extraction_fallback_model,
            input_tokens,
            output_tokens,
            cost_cents(settings.llm_extraction_fallback_model, input_tokens, output_tokens),
        )
        try:
            return model_cls.model_validate(json.loads(text))
        except (json.JSONDecodeError, ValidationError):
            continue

    return None
