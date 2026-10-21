import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data" / "java_vacancies.csv"
OUTPUT = ROOT / "results" / "regions"

REGIONS = [
    "Москва",
    "Санкт-Петербург",
    "Новосибирск",
]


def main():
    if not SOURCE.exists():
        raise FileNotFoundError(f"Не найден файл: {SOURCE}")

    OUTPUT.mkdir(parents=True, exist_ok=True)

    totals = Counter()
    skills_by_region = {region: Counter() for region in REGIONS}

    with SOURCE.open(
        "r", encoding="utf-8-sig", newline=""
    ) as file:
        reader = csv.DictReader(file)

        required = {"area", "key_skills"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"В CSV отсутствуют колонки: {missing}")

        for row in reader:
            region = (row.get("area") or "").strip()

            if region not in skills_by_region:
                continue

            totals[region] += 1

            # Один навык учитываем не более одного раза
            # в рамках одной вакансии.
            skills = {
                item.strip().casefold()
                for item in (row.get("key_skills") or "").split(";")
                if item.strip()
            }
            skills_by_region[region].update(skills)

    output_file = OUTPUT / "skills_by_region.csv"

    with output_file.open(
        "w", encoding="utf-8-sig", newline=""
    ) as file:
        writer = csv.writer(file)
        writer.writerow([
            "region",
            "skill",
            "vacancy_count",
            "region_vacancies",
            "percent_of_region_vacancies",
        ])

        for region in REGIONS:
            total = totals[region]

            print(f"\n{region}")
            print(f"Всего вакансий: {total}")
            print("Топ-15 навыков:")

            for skill, count in skills_by_region[region].most_common(15):
                percent = count / total * 100 if total else 0

                print(
                    f"  {skill}: {count} вакансий "
                    f"({percent:.2f}%)"
                )

            for skill, count in skills_by_region[region].most_common():
                percent = count / total * 100 if total else 0
                writer.writerow([
                    region,
                    skill,
                    count,
                    total,
                    round(percent, 2),
                ])

    print(f"\nCSV сохранён: {output_file}")


if __name__ == "__main__":
    main()
