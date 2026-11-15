import os
import subprocess
import sys


def _thresholds_with(env: dict) -> str:
    code = (
        "from ml_service.ml.targets.target_calculator import TargetCalculator as T; "
        "print(T.CRITICAL_ABSENCE_THRESHOLD, T.CRITICAL_GRADE_THRESHOLD)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], env={**os.environ, **env}, capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def test_admission_thresholds_come_from_the_environment():
    assert _thresholds_with({"ADMISSION_ABSENCE_THRESHOLD": "70", "ADMISSION_GRADE_THRESHOLD": "60"}) == "70.0 60.0"


def test_admission_thresholds_default_to_the_university_rule():
    env = {k: v for k, v in os.environ.items() if not k.startswith("ADMISSION_")}
    code = (
        "import dotenv; dotenv.load_dotenv = lambda *a, **k: None; "
        "from ml_service.ml.targets.target_calculator import TargetCalculator as T; "
        "print(T.CRITICAL_ABSENCE_THRESHOLD, T.CRITICAL_GRADE_THRESHOLD)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], env={**env, "IMPORT_SERVICE_URL": "http://test"},
        capture_output=True, text=True, check=True,
    )

    assert result.stdout.strip() == "75.0 50.0"
