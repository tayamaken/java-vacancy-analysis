import csv
from collections import Counter
from pathlib import Path

source = Path(r"D:\ITMO\DataEng\rustfs-data\it_vacancies_2024.csv")
target = Path(r"D:\ITMO\DataEng\java-vacancy-analysis\data\java_vacancies.csv")

target.parent.mkdir(parents=True, exist_ok=True)

target_role = "\u041f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u0438\u0441\u0442, \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u0447\u0438\u043a"

selected = 0
ids = set()
areas = Counter()
salary_rows = 0

with source.open("r", encoding="utf-8-sig", newline="") as fin:
    reader = csv.DictReader(fin)

    with target.open("w", encoding="utf-8-sig", newline="") as fout:
        writer = csv.DictWriter(fout, fieldnames=reader.fieldnames)
        writer.writeheader()

        for row in reader:
            name = (row.get("name") or "").strip()
            role = (row.get("role") or "").strip()

            if "java" not in name.casefold() or role != target_role:
                continue

            writer.writerow(row)
            selected += 1

            vacancy_id = (row.get("vacancy_id") or "").strip()
            if vacancy_id:
                ids.add(vacancy_id)

            areas[(row.get("area") or "").strip()] += 1

            if (row.get("salary_from") or "").strip() or (row.get("salary_to") or "").strip():
                salary_rows += 1

print("Selected CSV:", target)
print("Selected rows:", selected)
print("Unique vacancy IDs:", len(ids))
print("Rows beyond unique IDs:", selected - len(ids))
print("Rows with salary data:", salary_rows)
print("Top 10 areas:")
for area, count in areas.most_common(10):
    print(repr(area), count)
print("Output size (bytes):", target.stat().st_size)
