from dataclasses import dataclass

from app.models.finding import Finding


class DeliveryFailed(Exception):
    """A provider call failed in a way that's worth retrying. Callers catch
    this at the task boundary and record it on the `alert` row — it never
    propagates past app.tasks.delivery uncaught (docs/backend-rules.md:
    catch exceptions you can handle)."""


@dataclass
class AlertMessage:
    """What every channel kind renders from — built once per delivery
    attempt so each sender only needs to know its own formatting, not how
    to read a Finding."""

    competitor_name: str
    title: str
    summary: str
    urgency: str
    change_type: str
    detail_url: str

    @classmethod
    def from_finding(cls, finding: Finding, competitor_name: str, detail_url: str) -> "AlertMessage":
        return cls(
            competitor_name=competitor_name,
            title=finding.title,
            summary=finding.summary,
            urgency=finding.urgency.value,
            change_type=finding.change_type.value,
            detail_url=detail_url,
        )
