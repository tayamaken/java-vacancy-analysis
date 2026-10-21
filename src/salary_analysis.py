import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path


SOURCE = Path("data/java_vacancies.csv")
OUTPUT = Path("results/salary")


def parse_salary(value):
    """Преобразует зарплату в число; пустые и некорректные значения пропускает."""
    if value is None:
        return None

    value = value.strip().replace("\u00a0", "").replace(" ", "").replace(",", ".")

    if not value:
        return None

    try:
        number = float(value)
    except ValueError:
        return None

    if not math.isfinite(number):
        return None

    return number


def percentile(values, p):
    """Линейно интерполируемый перцентиль без сторонних библиотек."""
    ordered = sorted(values)

    if not ordered:
        return None

    position = (len(ordered) - 1) * p
    left = math.floor(position)
    right = math.ceil(position)

    if left == right:
        return ordered[left]

    return ordered[left] + (ordered[right] - ordered[left]) * (position - left)


def save_csv(path, rows, fields):
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)

    with SOURCE.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    total = len(rows)

    if total == 0:
        raise ValueError(f"В файле нет строк: {SOURCE}")

    quality = Counter()
    currencies = Counter()
    gross_values = Counter()
    salary_by_currency = defaultdict(lambda: defaultdict(list))
    paired_ranges_by_currency = defaultdict(list)

    invalid_numeric = Counter()
    inverted_ranges = 0

    for row in rows:
        salary_from_raw = row.get("salary_from", "")
        salary_to_raw = row.get("salary_to", "")
        currency_raw = row.get("currency", "")
        gross_raw = row.get("gross", "")

        salary_from = parse_salary(salary_from_raw)
        salary_to = parse_salary(salary_to_raw)

        has_from = bool(salary_from_raw and salary_from_raw.strip())
        has_to = bool(salary_to_raw and salary_to_raw.strip())
        has_currency = bool(currency_raw and currency_raw.strip())

        quality["salary_from_filled"] += has_from
        quality["salary_to_filled"] += has_to
        quality["both_salary_fields_filled"] += has_from and has_to
        quality["only_salary_from_filled"] += has_from and not has_to
        quality["only_salary_to_filled"] += has_to and not has_from
        quality["both_salary_fields_empty"] += not has_from and not has_to

        if has_from and salary_from is None:
            invalid_numeric["salary_from"] += 1

        if has_to and salary_to is None:
            invalid_numeric["salary_to"] += 1

        currency = currency_raw.strip().upper() if has_currency else "(не указана)"
        currencies[currency] += 1

        gross = gross_raw.strip() if gross_raw and gross_raw.strip() else "(не указан)"
        gross_values[gross] += 1

        if salary_from is not None:
            salary_by_currency[currency]["salary_from"].append(salary_from)

        if salary_to is not None:
            salary_by_currency[currency]["salary_to"].append(salary_to)

        if salary_from is not None and salary_to is not None:
            if salary_from > salary_to:
                inverted_ranges += 1

            paired_ranges_by_currency[currency].append(
                (salary_from, salary_to)
            )

    # 1. Общая проверка заполненности зарплатных полей.
    quality_rows = [
        {
            "metric": metric,
            "count": count,
            "percent_of_all_vacancies": round(count / total * 100, 2),
        }
        for metric, count in quality.items()
    ]

    quality_rows.extend([
        {
            "metric": "invalid_salary_from_values",
            "count": invalid_numeric["salary_from"],
            "percent_of_all_vacancies": round(
                invalid_numeric["salary_from"] / total * 100, 2
            ),
        },
        {
            "metric": "invalid_salary_to_values",
            "count": invalid_numeric["salary_to"],
            "percent_of_all_vacancies": round(
                invalid_numeric["salary_to"] / total * 100, 2
            ),
        },
        {
            "metric": "salary_from_greater_than_salary_to",
            "count": inverted_ranges,
            "percent_of_all_vacancies": round(inverted_ranges / total * 100, 2),
        },
    ])

    save_csv(
        OUTPUT / "salary_quality.csv",
        quality_rows,
        ["metric", "count", "percent_of_all_vacancies"],
    )

    # 2. Число вакансий в каждой валюте.
    currency_rows = [
        {
            "currency": currency,
            "vacancy_count": count,
            "percent_of_all_vacancies": round(count / total * 100, 2),
        }
        for currency, count in currencies.most_common()
    ]

    save_csv(
        OUTPUT / "salary_by_currency.csv",
        currency_rows,
        ["currency", "vacancy_count", "percent_of_all_vacancies"],
    )

    # 3. Распределение признака gross.
    gross_rows = [
        {
            "gross": gross,
            "vacancy_count": count,
            "percent_of_all_vacancies": round(count / total * 100, 2),
        }
        for gross, count in gross_values.most_common()
    ]

    save_csv(
        OUTPUT / "salary_gross.csv",
        gross_rows,
        ["gross", "vacancy_count", "percent_of_all_vacancies"],
    )

    # 4. Описательная статистика зарплат отдельно по валютам и границам.
    summary_rows = []

    for currency, fields in sorted(salary_by_currency.items()):
        for field_name, values in sorted(fields.items()):
            if not values:
                continue

            summary_rows.append({
                "currency": currency,
                "salary_field": field_name,
                "count": len(values),
                "min": round(min(values), 2),
                "p25": round(percentile(values, 0.25), 2),
                "median": round(statistics.median(values), 2),
                "mean": round(statistics.mean(values), 2),
                "p75": round(percentile(values, 0.75), 2),
                "max": round(max(values), 2),
            })

    save_csv(
        OUTPUT / "salary_numeric_summary.csv",
        summary_rows,
        [
            "currency", "salary_field", "count", "min",
            "p25", "median", "mean", "p75", "max",
        ],
    )

    # 5. Статистика диапазона зарплат, только когда обе границы известны.
    range_rows = []

    for currency, ranges in sorted(paired_ranges_by_currency.items()):
        if not ranges:
            continue

        widths = [upper - lower for lower, upper in ranges]

        range_rows.append({
            "currency": currency,
            "vacancies_with_both_bounds": len(ranges),
            "median_salary_from": round(
                statistics.median(lower for lower, _ in ranges), 2
            ),
            "median_salary_to": round(
                statistics.median(upper for _, upper in ranges), 2
            ),
            "median_range_width": round(statistics.median(widths), 2),
            "inverted_ranges": sum(lower > upper for lower, upper in ranges),
        })

    save_csv(
        OUTPUT / "salary_ranges.csv",
        range_rows,
        [
            "currency", "vacancies_with_both_bounds",
            "median_salary_from", "median_salary_to",
            "median_range_width", "inverted_ranges",
        ],
    )

    print(f"Всего вакансий: {total}")
    print(f"Результаты сохранены в: {OUTPUT.resolve()}")

    print("\nЗаполненность зарплат:")
    for item in quality_rows:
        print(
            f"  {item['metric']}: {item['count']} "
            f"({item['percent_of_all_vacancies']}%)"
        )

    print("\nВалюты:")
    for item in currency_rows:
        print(
            f"  {item['currency']}: {item['vacancy_count']} "
            f"({item['percent_of_all_vacancies']}%)"
        )

    print("\nСтатистика зарплат по валютам:")
    for item in summary_rows:
        print(
            f"  {item['currency']} / {item['salary_field']}: "
            f"n={item['count']}, median={item['median']}, "
            f"mean={item['mean']}"
        )


if __name__ == "__main__":
    main()
