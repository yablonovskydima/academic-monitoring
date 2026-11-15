import os
import subprocess
import sys


def test_admission_rule_reads_the_shared_thresholds_from_the_environment():
    code = (
        "from insights_service.insights.risk_levels import assess_admission; "
        "level, reasons = assess_admission({'study_mode': 'full_time', 'lecture_absence_percent': 71.0, "
        "'lab_absence_percent': 0.0, 'avg_grade': 80.0}); "
        "print(level.value, '|', reasons[0].text)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        env={
            **os.environ,
            "ADMISSION_ABSENCE_THRESHOLD": "70",
            "ADMISSION_GRADE_THRESHOLD": "50",
            "PYTHONIOENCODING": "utf-8",
        },
        capture_output=True, encoding="utf-8", check=True,
    )

    assert result.stdout.strip() == "high | Lecture absences: 71% — admission threshold is 70%"
