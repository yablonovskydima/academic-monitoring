import csv
import random

from faker import Faker

from import_service.generator import config

fake = Faker("uk_UA")


def generate_groups() -> list[dict]:
    groups = []
    for i in range(config.GROUPS_COUNT):
        groups.append({
            "id": i + 1,
            "name": f"КН-{20 + i}",
            "faculty": config.FACULTY,
            "course_year": random.randint(1, 4),
        })
    return groups


def generate_students(groups: list[dict]) -> list[dict]:
    students = []
    study_modes = list(config.STUDY_MODE_WEIGHTS.keys())
    weights = list(config.STUDY_MODE_WEIGHTS.values())

    student_id = 1
    for group in groups:
        for _ in range(config.STUDENTS_PER_GROUP):
            students.append({
                "id": student_id,
                "full_name": fake.name(),
                "group_id": group["id"],
                "email": fake.unique.email(),
                "study_mode": random.choices(study_modes, weights=weights)[0],
            })
            student_id += 1
    return students


def write_csv(rows: list[dict], filename: str) -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    filepath = config.DATA_DIR / filename

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Written {len(rows)} rows to {filepath}")


def run_generate():
    groups = generate_groups()
    write_csv(groups, "groups.csv")

    students = generate_students(groups)
    write_csv(students, "students.csv")


if __name__ == "__main__":
    run_generate()