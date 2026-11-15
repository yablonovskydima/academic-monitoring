import enum


class IndexCategory(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"


class RiskType(str, enum.Enum):
    expulsion = "expulsion"
    academic_debt = "academic_debt"
    exam_admission_denial = "exam_admission_denial"


class RiskKind(str, enum.Enum):
    status = "status"
    forecast = "forecast"


class RiskLevel(str, enum.Enum):
    low = "low"
    moderate = "moderate"
    high = "high"


class InsightTarget(str, enum.Enum):
    index = "index"
    expulsion = "expulsion"
    academic_debt = "academic_debt"
    exam_admission_denial = "exam_admission_denial"


class Theme(str, enum.Enum):
    grades = "grades"
    attendance = "attendance"
    submissions = "submissions"
    trend = "trend"
    context = "context"


class ReasonDirection(str, enum.Enum):
    risk = "risk"
    protective = "protective"


class ReasonStrength(str, enum.Enum):
    main = "main"
    significant = "significant"
    minor = "minor"


class ChangeKind(str, enum.Enum):
    index_category = "index_category"
    risk_level = "risk_level"


class ChangeDirection(str, enum.Enum):
    worsened = "worsened"
    improved = "improved"
