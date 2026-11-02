import pytest

from import_service.services.student_semester_features_service import course_year_at


@pytest.mark.parametrize("academic_year,expected", [
    ("2025/2026", 3),
    ("2024/2025", 2),
    ("2023/2024", 1),
])
def test_course_year_counts_back_from_the_groups_current_year(academic_year, expected):
    assert course_year_at(3, academic_year, "2025/2026") == expected


def test_course_year_never_drops_below_one():
    assert course_year_at(1, "2023/2024", "2025/2026") == 1
