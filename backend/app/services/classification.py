import enum
import json
import uuid
from dataclasses import dataclass

import anthropic
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.llm.client import get_client
from app.llm.pricing import cost_cents
from app.llm.prompts.classification_v1 import SYSTEM_PROMPT, build_user_message
from app.models.llm_usage import LlmPurpose
from app.models.source import SourceType
from app.repositories import finding_feedback as finding_feedback_repo
from app.repositories import llm_usage as llm_usage_repo
from app.repositories import workspaces as workspaces_repo
from app.schemas.classification import ClassificationResult
from app.schemas.extraction_fields import Changeset
from app.services.llm_budget import BudgetStatus, check_budget

_MAX_RETRIES = 1


class ClassificationOutcome(str, enum.Enum):
    success = "success"
    failed = "failed"
    budget_exhausted = "budget_exhausted"


@dataclass
class ClassificationResponse:
    outcome: ClassificationOutcome
    result: ClassificationResult | None = None


def _output_schema() -> dict:
    schema = ClassificationResult.model_json_schema()
    schema["additionalProperties"] = False
    return schema


async def _call_model(client: anthropic.AsyncAnthropic, user_message: str) -> tuple[str, int, int]:
    response = await client.messages.create(
        model=settings.llm_classification_model,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        output_config={"format": {"type": "json_schema", "schema": _output_schema()}},
        messages=[{"role": "user", "content": user_message}],
    )
    text = next(block.text for block in response.content if block.type == "text")
    return text, response.usage.input_tokens, response.usage.output_tokens


async def classify(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    competitor_name: str,
    source_type: SourceType,
    changeset: Changeset,
) -> ClassificationResponse:
    """Never let a malformed model response touch the DB unvalidated
    (docs/rules.md), never drop the finding on failure, and always write
    an llm_usage row for every call actually made — including a failed
    retry, since it was still billed."""
    workspace = await workspaces_repo.get_by_id(db, workspace_id)
    if workspace is None:
        return ClassificationResponse(ClassificationOutcome.failed)

    if await check_budget(db, workspace) == BudgetStatus.hard_stop:
        return ClassificationResponse(ClassificationOutcome.budget_exhausted)

    feedback_examples = await finding_feedback_repo.recent_for_prompt(db, workspace_id)
    user_message = build_user_message(competitor_name, source_type, changeset, feedback_examples)[
        : settings.llm_max_input_chars
    ]

    client = get_client()
    last_error: Exception | None = None
    for _attempt in range(_MAX_RETRIES + 1):
        text, input_tokens, output_tokens = await _call_model(client, user_message)
        await llm_usage_repo.create(
            db,
            workspace_id,
            LlmPurpose.classification,
            settings.llm_classification_model,
            input_tokens,
            output_tokens,
            cost_cents(settings.llm_classification_model, input_tokens, output_tokens),
        )
        try:
            parsed = ClassificationResult.model_validate(json.loads(text))
            return ClassificationResponse(ClassificationOutcome.success, parsed)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc

    assert last_error is not None
    return ClassificationResponse(ClassificationOutcome.failed)
