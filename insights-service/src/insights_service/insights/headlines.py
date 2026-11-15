from dataclasses import dataclass

from insights_service.insights.feature_catalog import RISK_LABELS
from insights_service.insights.reasons import ReasonDraft
from insights_service.models.enums import IndexCategory, ReasonDirection, RiskKind, RiskLevel, RiskType, Theme


@dataclass(frozen=True)
class RiskDraft:
    risk_type: RiskType
    kind: RiskKind
    level: RiskLevel
    probability: float
    reasons: list[ReasonDraft]


@dataclass(frozen=True)
class Headline:
    text: str
    theme: Theme | None
    needs_attention: bool


FORECAST_RISKS = (RiskType.expulsion, RiskType.academic_debt)


def compose_headline(
    index_category: IndexCategory,
    index_reasons: list[ReasonDraft],
    risks: list[RiskDraft],
) -> Headline:
    by_type = {risk.risk_type: risk for risk in risks}
    admission = by_type.get(RiskType.exam_admission_denial)

    if admission is not None and admission.level is RiskLevel.high:
        first = _first_risk_reason(admission.reasons)
        text = "Not admitted to exams" + (f". {first.text}" if first else "")
        return Headline(text, first.theme if first else None, needs_attention=True)

    for risk_type in FORECAST_RISKS:
        risk = by_type.get(risk_type)
        if risk is not None and risk.level is RiskLevel.high:
            return _with_cause(f"High risk of {RISK_LABELS[risk_type]}", risk.reasons)

    if index_category is IndexCategory.low:
        return _with_cause("Low academic index", index_reasons)

    concerns = []
    if admission is not None and admission.level is RiskLevel.moderate:
        concerns.append("close to the exam admission threshold")
    for risk_type in FORECAST_RISKS:
        risk = by_type.get(risk_type)
        if risk is not None and risk.level is RiskLevel.moderate:
            concerns.append(f"moderate risk of {RISK_LABELS[risk_type]}")
    if index_category is IndexCategory.medium:
        concerns.append("medium academic index")

    if concerns:
        return Headline("Needs attention: " + ", ".join(concerns), None, needs_attention=False)

    return Headline("No significant risks", None, needs_attention=False)


def _with_cause(text: str, reasons: list[ReasonDraft]) -> Headline:
    first = _first_risk_reason(reasons)
    if first is None:
        return Headline(text, None, needs_attention=True)
    return Headline(f"{text}. Main reason: {first.title.lower()}", first.theme, needs_attention=True)


def _first_risk_reason(reasons: list[ReasonDraft]) -> ReasonDraft | None:
    return next((reason for reason in reasons if reason.direction is ReasonDirection.risk), None)
