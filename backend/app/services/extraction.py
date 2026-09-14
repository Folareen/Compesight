import re

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page

from app.schemas.extraction_fields import PricingPageFields, PricingTier, SourceConfig, WebsitePageFields

_PRICE_PATTERN = re.compile(
    r"(?P<currency>[$€£])\s?(?P<amount>[\d,]+(?:\.\d{2})?)|(?P<amount2>[\d,]+(?:\.\d{2})?)\s?(?P<currency2>USD|EUR|GBP)",
    re.IGNORECASE,
)
_HEADING_SELECTOR = "h1, h2, h3, h4, [class*='title' i], [class*='name' i], [class*='heading' i]"
_MONTHLY_PATTERN = re.compile(r"\b(month|mo\.?)\b", re.IGNORECASE)
_ANNUAL_PATTERN = re.compile(r"\b(annual|year|yr\.?)\b", re.IGNORECASE)
_ONE_TIME_PATTERN = re.compile(r"\bone[\s-]?time\b", re.IGNORECASE)
_HIGHLIGHT_PATTERN = re.compile(r"popular|highlighted|recommended|featured", re.IGNORECASE)

_CURRENCY_SYMBOL_MAP = {"$": "USD", "€": "EUR", "£": "GBP"}
_MIN_TIER_CARDS = 2
_BODY_DIGEST_CAP = 20_000


class ExtractionFailed(Exception):
    """Raised when the extraction heuristic can't confidently find the
    expected content. The caller must never write an extraction row with
    empty/degenerate fields on this — an empty tiers list would be
    indistinguishable from "they deleted all pricing", which is the exact
    false-alarm docs/rules.md warns about."""


def _parse_price(text: str) -> tuple[int, str] | None:
    match = _PRICE_PATTERN.search(text)
    if match is None:
        return None
    amount_str = match.group("amount") or match.group("amount2")
    currency_symbol = match.group("currency")
    currency_code = match.group("currency2")
    currency = _CURRENCY_SYMBOL_MAP.get(currency_symbol, currency_symbol) if currency_symbol else currency_code
    if currency is None:
        return None
    try:
        amount = float(amount_str.replace(",", ""))
    except ValueError:
        return None
    return round(amount * 100), currency.upper()


def _billing_period(text: str) -> str:
    if _MONTHLY_PATTERN.search(text):
        return "monthly"
    if _ANNUAL_PATTERN.search(text):
        return "annual"
    if _ONE_TIME_PATTERN.search(text):
        return "one_time"
    return "unknown"


_CARD_MATCH_SELECTOR = (
    f":has({_HEADING_SELECTOR}):has-text('$'), "
    f":has({_HEADING_SELECTOR}):has-text('€'), "
    f":has({_HEADING_SELECTOR}):has-text('£')"
)


async def _find_tier_cards(page: Page):
    """Locate the innermost elements that each contain a heading-like
    element and a currency-formatted price. Matching by `:has-text()`
    alone would also match every ancestor of a real card (the whole grid,
    the body, ...), since text content propagates upward — so this keeps
    only matches that themselves contain no *other* match, i.e. the leaf
    cards, by checking each candidate for a nested candidate under it."""
    candidates = page.locator(_CARD_MATCH_SELECTOR)
    count = await candidates.count()

    leaves = []
    for i in range(count):
        candidate = candidates.nth(i)
        nested_count = await candidate.locator(_CARD_MATCH_SELECTOR).count()
        if nested_count == 0:
            leaves.append(candidate)
    return leaves


async def extract_pricing_page(page: Page, config: SourceConfig) -> PricingPageFields:
    """Generic DOM heuristic for pricing pages — no LLM, no per-source
    selector UI yet (Phase 2). If `config.selector_override` is set, it
    names the tier-card container selector directly; otherwise cards are
    found by locating elements that contain both a heading-like element
    and a currency-formatted price, requiring at least two such cards to
    call it a tier list.

    Raises ExtractionFailed rather than returning `tiers: []` when fewer
    than two cards are found — see the module docstring's warning about
    false alarms.
    """
    if config.selector_override is not None:
        card_locator = page.locator(config.selector_override)
        count = await card_locator.count()
        if count < _MIN_TIER_CARDS:
            raise ExtractionFailed(f"found {count} candidate pricing cards, need at least {_MIN_TIER_CARDS}")
        cards = [card_locator.nth(i) for i in range(count)]
    else:
        cards = await _find_tier_cards(page)
        if len(cards) < _MIN_TIER_CARDS:
            raise ExtractionFailed(
                f"found {len(cards)} candidate pricing cards, need at least {_MIN_TIER_CARDS}"
            )

    tiers: list[PricingTier] = []
    for card in cards:
        card_text = await card.inner_text()

        price = _parse_price(card_text)
        if price is None:
            continue

        heading_locator = card.locator(_HEADING_SELECTOR).first
        try:
            name = (await heading_locator.inner_text()).strip()
        except PlaywrightError:
            continue
        if not name:
            continue

        feature_locator = card.locator("li")
        feature_count = await feature_locator.count()
        features = sorted(
            {
                text.strip()
                for j in range(feature_count)
                if (text := await feature_locator.nth(j).inner_text()).strip()
            }
        )

        price_minor_units, currency = price
        tiers.append(
            PricingTier(
                name=name,
                price_minor_units=price_minor_units,
                currency=currency,
                billing_period=_billing_period(card_text),
                features=features,
                highlighted=bool(_HIGHLIGHT_PATTERN.search(card_text)),
            )
        )

    if len(tiers) < _MIN_TIER_CARDS:
        raise ExtractionFailed(
            f"only {len(tiers)} candidate cards had a parseable price, need at least {_MIN_TIER_CARDS}"
        )

    return PricingPageFields(tiers=tiers)


async def extract_website_page(page: Page, config: SourceConfig) -> WebsitePageFields:
    """Minimal, best-effort extraction for plain `website` sources — there
    is no fixed pricing-style schema to target, so this captures the title
    and a normalized, capped digest of visible body text. Deliberately
    coarse; `website` sources aren't part of Phase 1's done condition."""
    title = await page.title()
    body_text = await page.locator("body").inner_text()
    digest = " ".join(body_text.split())[:_BODY_DIGEST_CAP]
    return WebsitePageFields(title=title.strip(), body_digest=digest)
