from typing import Literal

from pydantic import BaseModel, ConfigDict


class PricingTier(BaseModel):
    name: str
    price_minor_units: int
    currency: str
    billing_period: Literal["monthly", "annual", "one_time", "unknown"]
    features: list[str]
    highlighted: bool


class PricingPageFields(BaseModel):
    schema_version: Literal[1] = 1
    tiers: list[PricingTier]


class WebsitePageFields(BaseModel):
    schema_version: Literal[1] = 1
    title: str
    body_digest: str


ExtractionFields = PricingPageFields | WebsitePageFields


class SourceConfig(BaseModel):
    """Per-source override for the generic extraction heuristic.

    Phase 1 has no selector-configuration UI — this is the field Phase 2's
    UI will write to. Don't add more fields speculatively before then.
    """

    model_config = ConfigDict(extra="forbid")

    selector_override: str | None = None
    ignore_fields: list[str] = []


class FieldChange(BaseModel):
    path: str
    old_value: str | int | bool | list[str] | None
    new_value: str | int | bool | list[str] | None


class Changeset(BaseModel):
    fields: list[FieldChange]
