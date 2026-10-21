import csv
from pathlib import Path

ROOT = Path("results")
MAPREDUCE = ROOT / "mapreduce_chunked" / "256KB"
DUCKDB = ROOT / "duckdb" / "sql"
OUTPUT = ROOT / "comparison"
OUTPUT.mkdir(parents=True, exist_ok=True)

FILES = {
    "skills.csv": ["skill", "vacancy_count"],
    "skill_pairs.csv": ["skill_1", "skill_2", "vacancy_count"],
    "skill_triples.csv": [
        "skill_1", "skill_2", "skill_3", "vacancy_count"
    ],
}


def load_csv(path, columns):
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        result = {}
        for row in reader:
            key = tuple(row[column].strip().casefold()
                        for column in columns[:-1])
            result[key] = int(row[columns[-1]])
        return result


all_match = True

for filename, columns in FILES.items():
    mr_path = MAPREDUCE / filename
    sql_path = DUCKDB / filename

    if not mr_path.exists():
        print(f"НЕТ ФАЙЛА: {mr_path}")
        all_match = False
        continue

    if not sql_path.exists():
        print(f"НЕТ ФАЙЛА: {sql_path}")
        all_match = False
        continue

    mr = load_csv(mr_path, columns)
    sql = load_csv(sql_path, columns)

    only_mr = set(mr) - set(sql)
    only_sql = set(sql) - set(mr)
    different = {
        key: (mr[key], sql[key])
        for key in mr.keys() & sql.keys()
        if mr[key] != sql[key]
    }

    matched = not only_mr and not only_sql and not different
    all_match &= matched

    print(f"\n{filename}")
    print(f"  MapReduce: {len(mr)} комбинаций")
    print(f"  DuckDB:    {len(sql)} комбинаций")
    print(f"  Есть только в MapReduce: {len(only_mr)}")
    print(f"  Есть только в DuckDB:    {len(only_sql)}")
    print(f"  Различаются частоты:     {len(different)}")
    print(f"  Результат: {'СОВПАДАЮТ' if matched else 'ЕСТЬ РАСХОЖДЕНИЯ'}")

    if not matched:
        for key in list(only_mr)[:5]:
            print("  Только MapReduce:", key, mr[key])
        for key in list(only_sql)[:5]:
            print("  Только DuckDB:", key, sql[key])
        for key, counts in list(different.items())[:5]:
            print("  Разные частоты:", key, counts)

print("\nИТОГ:", "ВСЕ РЕЗУЛЬТАТЫ СОВПАЛИ" if all_match
      else "НУЖНО ИССЛЕДОВАТЬ РАСХОЖДЕНИЯ")
