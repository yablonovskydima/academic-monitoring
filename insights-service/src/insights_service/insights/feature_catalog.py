from dataclasses import dataclass

from insights_service.models.enums import RiskType, Theme


@dataclass(frozen=True)
class FeatureInfo:
    label: str
    theme: Theme
    higher_is_worse: bool | None = None
    unit: str = ""
    decimals: int = 0
    is_delta: bool = False
    min_change: float = 0.0


@dataclass(frozen=True)
class ThemeInfo:
    title: str
    action: str | None


FEATURES: dict[str, FeatureInfo] = {
    "avg_grade": FeatureInfo("Semester average grade", Theme.grades, higher_is_worse=False, decimals=1),
    "cumulative_avg_grade": FeatureInfo("Overall average grade", Theme.grades, higher_is_worse=False, decimals=1),
    "grade_stddev": FeatureInfo("Grade spread", Theme.grades, higher_is_worse=True, decimals=1),
    "lecture_absence_percent": FeatureInfo("Lecture absences", Theme.attendance, higher_is_worse=True, unit="%"),
    "lab_absence_percent": FeatureInfo("Lab absences", Theme.attendance, higher_is_worse=True, unit="%"),
    "absence_percent": FeatureInfo("Absences", Theme.attendance, higher_is_worse=True, unit="%"),
    "unworked_absences_count": FeatureInfo("Absences not made up", Theme.attendance, higher_is_worse=True),
    "cumulative_absence_percent": FeatureInfo("Overall absences", Theme.attendance, higher_is_worse=True, unit="%"),
    "missing_submissions_count": FeatureInfo("Missing submissions", Theme.submissions, higher_is_worse=True),
    "late_submissions_count": FeatureInfo("Late submissions", Theme.submissions, higher_is_worse=True),
    "cumulative_avg_missing_submissions": FeatureInfo(
        "Missing submissions per semester (avg)", Theme.submissions, higher_is_worse=True, decimals=1,
    ),
    "cumulative_avg_late_submissions": FeatureInfo(
        "Late submissions per semester (avg)", Theme.submissions, higher_is_worse=True, decimals=1,
    ),
    "avg_grade_delta": FeatureInfo(
        "Average grade vs. last semester", Theme.trend, higher_is_worse=False, decimals=1,
        is_delta=True, min_change=3.0,
    ),
    "absence_percent_delta": FeatureInfo(
        "Absences vs. last semester", Theme.trend, higher_is_worse=True, unit=" p.p.",
        is_delta=True, min_change=5.0,
    ),
    "missing_submissions_delta": FeatureInfo(
        "Missing submissions vs. last semester", Theme.trend, higher_is_worse=True,
        is_delta=True, min_change=2.0,
    ),
    "course_year": FeatureInfo("Course year", Theme.context),
    "study_mode_full_time": FeatureInfo("Study mode", Theme.context),
    "study_mode_part_time": FeatureInfo("Study mode", Theme.context),
    "study_mode_individual_schedule": FeatureInfo("Study mode", Theme.context),
    "semesters_completed_count": FeatureInfo("Semesters completed", Theme.context),
}

THEMES: dict[Theme, ThemeInfo] = {
    Theme.grades: ThemeInfo(
        "Grades",
        "Find out which subjects are causing difficulty and offer consultations with the teachers.",
    ),
    Theme.attendance: ThemeInfo(
        "Attendance",
        "Discuss the reasons for the absences and agree on making up the missed classes.",
    ),
    Theme.submissions: ThemeInfo(
        "Submissions",
        "Check which assignments are missing or late and agree on deadlines.",
    ),
    Theme.trend: ThemeInfo(
        "Trend",
        "Find out what has changed since last semester.",
    ),
    Theme.context: ThemeInfo("Context", None),
}

RISK_LABELS: dict[RiskType, str] = {
    RiskType.expulsion: "expulsion",
    RiskType.academic_debt: "academic debt",
    RiskType.exam_admission_denial: "exam admission denial",
}


def feature_info(feature_name: str) -> FeatureInfo:
    return FEATURES.get(feature_name, FeatureInfo(feature_name, Theme.context))


def format_value(info: FeatureInfo, value: float) -> str:
    sign = "+" if info.is_delta else ""
    return f"{value:{sign}.{info.decimals}f}{info.unit}"
