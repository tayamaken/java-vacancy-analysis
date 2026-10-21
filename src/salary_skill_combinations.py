import csv
import math
import statistics
from collections import defaultdict
from itertools import combinations
from pathlib import Path


SOURCE = Path("data/java_vacancies.csv")
OUTPUT = Path("results/salary/skill_combinations")

# Учитываем группы, в которых есть хотя бы 5 вакансий
MIN_VACANCIES = 5
CURRENCY = "RUR"


def parse_salary(value):
    """Преобразует строку зарплаты в конечное число или None."""
    if not value:
        return None

    value = value.strip().replace("\u00a0", "").replace(" ", "")
    value = value.replace(",", ".")

    try:
        number = float(value)
    except ValueError:
        return None

    if not math.isfinite(number) or number < 0:
        return None

    return number


def get_salary(row):
    """Одна оценка зарплаты на вакансию."""
    lower = parse_salary(row.get("salary_from", ""))
    upper = parse_salary(row.get("salary_to", ""))

    if lower is not None and upper is not None:
        if lower > upper:
            return None
        return (lower + upper) / 2

    if lower is not None:
        return lower

    if upper is not None:
        return upper

    return None


def get_skills(row):
    """Нормализует и убирает повторы навыков внутри вакансии."""
    raw = row.get("key_skills", "") or ""
    return sorted({
        skill.strip().casefold()
        for skill in raw.split(";")
        if skill.strip()
    })


def save_csv(path, rows):
    fields = [
        "combination",
        "vacancy_count",
        "median_salary",
        "mean_salary",
        "overall_median_salary",
        "difference_from_overall",
        "difference_percent",
    ]

    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)

    # Читаем подготовленный датасет.
    with SOURCE.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    total_rows = len(rows)
    currency_rows = [
        row for row in rows
        if (row.get("currency") or "").strip().upper() == CURRENCY
    ]

    # Для корректного сравнения зарплат используем только RUB.
    overall_salaries = []
    usable_vacancies = []

    no_salary = 0
    invalid_ranges = 0

    for row in currency_rows:
        lower = parse_salary(row.get("salary_from", ""))
        upper = parse_salary(row.get("salary_to", ""))

        if lower is not None and upper is not None and lower > upper:
            invalid_ranges += 1
            continue

        salary = get_salary(row)

        if salary is None:
            no_salary += 1
            continue

        skills = get_skills(row)

        if not skills:
            continue

        overall_salaries.append(salary)
        usable_vacancies.append((salary, skills))

    if not overall_salaries:
        raise ValueError("Не найдено вакансий с зарплатой в RUR и навыками.")

    overall_median = statistics.median(overall_salaries)

    # Для каждого размера комбинации накапливаем зарплаты вакансий.
    grouped = {
        1: defaultdict(list),
        2: defaultdict(list),
        3: defaultdict(list),
    }

    for salary, skills in usable_vacancies:
        for size in (1, 2, 3):
            for combo in combinations(skills, size):
                grouped[size][combo].append(salary)

    output_names = {
        1: "skills_salary.csv",
        2: "pairs_salary.csv",
        3: "triples_salary.csv",
    }

    for size, groups in grouped.items():
        result = []

        for combo, salaries in groups.items():
            count = len(salaries)

            if count < MIN_VACANCIES:
                continue

            median_salary = statistics.median(salaries)
            difference = median_salary - overall_median

            result.append({
                "combination": " + ".join(combo),
                "vacancy_count": count,
                "median_salary": round(median_salary, 2),
                "mean_salary": round(statistics.mean(salaries), 2),
                "overall_median_salary": round(overall_median, 2),
                "difference_from_overall": round(difference, 2),
                "difference_percent": round(
                    difference / overall_median * 100, 2
                ) if overall_median else None,
            })

        # Сначала группы с самой высокой медианой.
        result.sort(
            key=lambda item: (
                item["median_salary"],
                item["vacancy_count"],
            ),
            reverse=True,
        )

        output_path = OUTPUT / output_names[size]
        save_csv(output_path, result)

        print(
            f"{output_path}: {len(result)} комбинаций "
            f"(минимум {MIN_VACANCIES} вакансий)"
        )

        print("  Наиболее высокая медиана:")
        for item in result[:5]:
            print(
                f"    {item['combination']}: "
                f"n={item['vacancy_count']}, "
                f"медиана={item['median_salary']:.0f} RUB, "
                f"отклонение={item['difference_percent']}%"
            )

        print("  Наиболее низкая медиана:")
        for item in sorted(
            result,
            key=lambda item: (
                item["median_salary"],
                -item["vacancy_count"],
            ),
        )[:5]:
            print(
                f"    {item['combination']}: "
                f"n={item['vacancy_count']}, "
                f"медиана={item['median_salary']:.0f} RUB, "
                f"отклонение={item['difference_percent']}%"
            )

    print("\nИтоги подготовки:")
    print(f"Всего вакансий в датасете: {total_rows}")
    print(f"Вакансий с валютой {CURRENCY}: {len(currency_rows)}")
    print(f"Вакансий с рассчитанной зарплатой и навыками: {len(usable_vacancies)}")
    print(f"Вакансий без доступной зарплаты: {no_salary}")
    print(f"Вакансий с перевёрнутым диапазоном: {invalid_ranges}")
    print(f"Общая медиана зарплаты: {overall_median:.2f} RUB")
    print(f"Результаты: {OUTPUT.resolve()}")


if __name__ == "__main__":
    main()
