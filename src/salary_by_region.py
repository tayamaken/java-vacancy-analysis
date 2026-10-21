import csv
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median

SOURCE = Path("data/java_vacancies.csv")
OUTPUT = Path("results/salary")

TARGET_REGIONS = {
    "Москва",
    "Санкт-Петербург",
    "Новосибирск",
}


def number(value):
    if not value or not value.strip():
        return None
    try:
        result = float(value.strip().replace("\u00a0", "").replace(" ", "").replace(",", "."))
        return result if result == result and abs(result) != float("inf") else None
    except ValueError:
        return None


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)

    total = Counter()
    salary_from = defaultdict(list)
    salary_to = defaultdict(list)
    both_bounds = Counter()

    with SOURCE.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            region = (row.get("area") or "").strip()

            if region not in TARGET_REGIONS:
                continue

            total[region] += 1

            currency = (row.get("currency") or "").strip().upper()
            if currency != "RUR":
                continue

            lower = number(row.get("salary_from"))
            upper = number(row.get("salary_to"))

            if lower is not None:
                salary_from[region].append(lower)
            if upper is not None:
                salary_to[region].append(upper)
            if lower is not None and upper is not None:
                both_bounds[region] += 1

    rows = []

    for region in sorted(TARGET_REGIONS):
        lower_values = salary_from[region]
        upper_values = salary_to[region]

        rows.append({
            "region": region,
            "all_vacancies": total[region],
            "rur_salary_from_count": len(lower_values),
            "rur_salary_from_median": round(median(lower_values), 2) if lower_values else "",
            "rur_salary_to_count": len(upper_values),
            "rur_salary_to_median": round(median(upper_values), 2) if upper_values else "",
            "rur_both_bounds_count": both_bounds[region],
        })

    output_file = OUTPUT / "salary_by_region.csv"
    with output_file.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print("Зарплаты по регионам (только RUR)")
    for row in rows:
        print(
            f"\n{row['region']}:"
            f"\n  Всего вакансий: {row['all_vacancies']}"
            f"\n  salary_from: n={row['rur_salary_from_count']}, "
            f"медиана={row['rur_salary_from_median']}"
            f"\n  salary_to: n={row['rur_salary_to_count']}, "
            f"медиана={row['rur_salary_to_median']}"
            f"\n  Обе границы: {row['rur_both_bounds_count']}"
        )

    print(f"\nCSV сохранён: {output_file.resolve()}")


if __name__ == "__main__":
    main()
