from collections.abc import Mapping
from typing import Any

from insights_service.config import (
    ADMISSION_ABSENCE_THRESHOLD,
    ADMISSION_ABSENCE_WARNING_MARGIN,
    ADMISSION_GRADE_THRESHOLD,
    ADMISSION_GRADE_WARNING_MARGIN,
    RISK_LEVEL_HIGH_THRESHOLD,
    RISK_LEVEL_MODERATE_THRESHOLD,
)
from insights_service.insights.feature_catalog import THEMES, feature_info, format_value
from insights_service.insights.reasons import ReasonDraft
from insights_service.models.enums import ReasonDirection, ReasonStrength, RiskLevel

ADMISSION_FEATURES = ("study_mode", "lecture_absence_percent", "lab_absence_percent", "avg_grade")
ABSENCE_FEATURES = ("lecture_absence_percent", "lab_absence_percent")


def forecast_level(probability: float) -> RiskLevel:
    if probability >= RISK_LEVEL_HIGH_THRESHOLD:
        return RiskLevel.high
    if probability >= RISK_LEVEL_MODERATE_THRESHOLD:
        return RiskLevel.moderate
    return RiskLevel.low


def supported_level(probability: float, reasons: list[ReasonDraft]) -> RiskLevel:
    level = forecast_level(probability)
    if level is not RiskLevel.low and not any(r.direction is ReasonDirection.risk for r in reasons):
        return RiskLevel.low
    return level


def assess_admission(features: Mapping[str, Any]) -> tuple[RiskLevel, list[ReasonDraft]] | None:
    if any(name not in features for name in ADMISSION_FEATURES):
        return None

    if features["study_mode"] != "full_time":
        return RiskLevel.low, []

    denied: list[ReasonDraft] = []
    near: list[ReasonDraft] = []

    for name in ABSENCE_FEATURES:
        value = float(features[name])
        if value >= ADMISSION_ABSENCE_THRESHOLD:
            denied.append(_rule_reason(
                name, value, f"admission threshold is {ADMISSION_ABSENCE_THRESHOLD:.0f}%", ReasonStrength.main,
            ))
        elif value >= ADMISSION_ABSENCE_THRESHOLD - ADMISSION_ABSENCE_WARNING_MARGIN:
            near.append(_rule_reason(
                name, value,
                f"{ADMISSION_ABSENCE_THRESHOLD - value:.0f} p.p. below the admission threshold "
                f"({ADMISSION_ABSENCE_THRESHOLD:.0f}%)",
                ReasonStrength.significant,
            ))

    grade = float(features["avg_grade"])
    if grade < ADMISSION_GRADE_THRESHOLD:
        denied.append(_rule_reason(
            "avg_grade", grade, f"minimum for admission is {ADMISSION_GRADE_THRESHOLD:.0f}", ReasonStrength.main,
        ))
    elif grade < ADMISSION_GRADE_THRESHOLD + ADMISSION_GRADE_WARNING_MARGIN:
        near.append(_rule_reason(
            "avg_grade", grade,
            f"only {grade - ADMISSION_GRADE_THRESHOLD:.1f} above the minimum for admission "
            f"({ADMISSION_GRADE_THRESHOLD:.0f})",
            ReasonStrength.significant,
        ))

    if denied:
        return RiskLevel.high, denied
    if near:
        return RiskLevel.moderate, near
    return RiskLevel.low, []


def _rule_reason(feature_name: str, value: float, note: str, strength: ReasonStrength) -> ReasonDraft:
    info = feature_info(feature_name)
    theme_info = THEMES[info.theme]
    return ReasonDraft(
        theme=info.theme,
        title=theme_info.title,
        direction=ReasonDirection.risk,
        strength=strength,
        text=f"{info.label}: {format_value(info, value)} — {note}",
        action=theme_info.action,
        feature_name=feature_name,
        feature_value=value,
        percentile=None,
    )
