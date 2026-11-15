from collections.abc import Iterable
from dataclasses import dataclass

from insights_service.config import MAX_REASONS, MIN_REASON_SHARE
from insights_service.insights.cohort import Cohort
from insights_service.insights.feature_catalog import THEMES, feature_info, format_value
from insights_service.models.enums import ReasonDirection, ReasonStrength, Theme
from insights_service.schemas.prediction_input import ContributionIn

MAIN_SHARE = 0.5
SIGNIFICANT_SHARE = 0.25
COMPARISON_MIN_SHARE = 0.5


@dataclass(frozen=True)
class ReasonDraft:
    theme: Theme
    title: str
    direction: ReasonDirection
    strength: ReasonStrength
    text: str
    action: str | None
    feature_name: str
    feature_value: float
    percentile: int | None


def build_reasons(
    contributions: Iterable[ContributionIn],
    cohort: Cohort,
    higher_output_is_worse: bool,
    max_reasons: int = MAX_REASONS,
    min_share: float = MIN_REASON_SHARE,
) -> list[ReasonDraft]:
    by_theme: dict[Theme, list[tuple[ContributionIn, float]]] = {}
    for contribution in contributions:
        theme = feature_info(contribution.feature_name).theme
        if theme is Theme.context:
            continue
        badness = contribution.shap_value if higher_output_is_worse else -contribution.shap_value
        by_theme.setdefault(theme, []).append((contribution, badness))

    totals = {theme: sum(badness for _, badness in items) for theme, items in by_theme.items()}
    total_weight = sum(abs(total) for total in totals.values())
    if total_weight == 0:
        return []

    reasons: list[ReasonDraft] = []
    for theme, total in sorted(totals.items(), key=lambda item: abs(item[1]), reverse=True):
        share = abs(total) / total_weight
        if total == 0 or share < min_share:
            continue

        direction = ReasonDirection.risk if total > 0 else ReasonDirection.protective
        reason = _describe_theme(theme, by_theme[theme], direction, share, cohort)
        if reason is not None:
            reasons.append(reason)
        if len(reasons) == max_reasons:
            break

    return reasons


def strength_for(share: float) -> ReasonStrength:
    if share >= MAIN_SHARE:
        return ReasonStrength.main
    if share >= SIGNIFICANT_SHARE:
        return ReasonStrength.significant
    return ReasonStrength.minor


def describe_feature(
    feature_name: str,
    value: float,
    direction: ReasonDirection,
    cohort: Cohort,
) -> tuple[str | None, int | None]:
    info = feature_info(feature_name)
    shown = f"{info.label}: {format_value(info, value)}"
    worse = direction is ReasonDirection.risk

    if info.is_delta:
        moved_worse = value > 0 if info.higher_is_worse else value < 0
        if value == 0 or abs(value) < info.min_change or moved_worse != worse:
            return None, None
        return shown, None

    if info.higher_is_worse is None:
        return shown, None

    if worse == info.higher_is_worse:
        share = cohort.share_below(feature_name, value)
    else:
        share = cohort.share_above(feature_name, value)

    if share is None or share < COMPARISON_MIN_SHARE:
        return shown, None

    word = "higher" if worse == info.higher_is_worse else "lower"
    percentile = min(99, round(share * 100))
    return f"{shown} — {word} than {percentile}% of students", percentile


def _describe_theme(
    theme: Theme,
    items: list[tuple[ContributionIn, float]],
    direction: ReasonDirection,
    share: float,
    cohort: Cohort,
) -> ReasonDraft | None:
    pointing_this_way = [
        (contribution, badness)
        for contribution, badness in items
        if badness != 0 and (badness > 0) == (direction is ReasonDirection.risk)
    ]

    for contribution, _ in sorted(pointing_this_way, key=lambda item: abs(item[1]), reverse=True):
        text, percentile = describe_feature(contribution.feature_name, contribution.feature_value, direction, cohort)
        if text is None:
            continue

        theme_info = THEMES[theme]
        return ReasonDraft(
            theme=theme,
            title=theme_info.title,
            direction=direction,
            strength=strength_for(share),
            text=text,
            action=theme_info.action if direction is ReasonDirection.risk else None,
            feature_name=contribution.feature_name,
            feature_value=contribution.feature_value,
            percentile=percentile,
        )

    return None
