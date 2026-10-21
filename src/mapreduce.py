import csv
import io
import itertools
import time
from collections import Counter
from pathlib import Path

import boto3


BUCKET = "hh-lake"
KEY = "java_developer_csv/java_vacancies.csv"
OUTPUT_DIR = Path("results/mapreduce")
S3_ENDPOINT = "http://localhost:9000"


def normalize_skills(value: str) -> list[str]:
    """Разделяет навыки, нормализует регистр и убирает дубликаты."""
    skills = {
        skill.strip().casefold()
        for skill in (value or "").split(";")
        if skill.strip()
    }
    return sorted(skills)


def save_counter(path: Path, header: list[str], counter: Counter) -> None:
    """Сохраняет комбинации в CSV от наиболее частых к редким."""
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(header)

        for combination, count in sorted(
            counter.items(),
            key=lambda item: (-item[1], item[0]),
        ):
            if isinstance(combination, tuple):
                writer.writerow([*combination, count])
            else:
                writer.writerow([combination, count])


def main() -> None:
    start_time = time.perf_counter()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    s3 = boto3.client("s3", endpoint_url=S3_ENDPOINT)

    print(f"Читаем s3://{BUCKET}/{KEY}")

    response = s3.get_object(Bucket=BUCKET, Key=KEY)

    skills_count = Counter()
    pairs_count = Counter()
    triples_count = Counter()

    rows_processed = 0
    rows_with_skills = 0

    # Важно: не используем with для response["Body"].
    # TextIOWrapper будет закрыт в finally после обработки CSV.
    body = response["Body"]
    text_stream = io.TextIOWrapper(
        body,
        encoding="utf-8-sig",
        newline="",
    )

    try:
        reader = csv.DictReader(text_stream)

        if "key_skills" not in (reader.fieldnames or []):
            raise ValueError("В CSV отсутствует столбец key_skills")

        for row in reader:
            rows_processed += 1
            skills = normalize_skills(row.get("key_skills", ""))

            if not skills:
                continue

            rows_with_skills += 1

            # Map: навыки, пары и тройки для каждой вакансии.
            skills_count.update(skills)
            pairs_count.update(itertools.combinations(skills, 2))
            triples_count.update(itertools.combinations(skills, 3))

    finally:
        text_stream.close()

    # Reduce: агрегируем количество появлений каждой комбинации.
    save_counter(
        OUTPUT_DIR / "skills.csv",
        ["skill", "vacancy_count"],
        skills_count,
    )
    save_counter(
        OUTPUT_DIR / "skill_pairs.csv",
        ["skill_1", "skill_2", "vacancy_count"],
        pairs_count,
    )
    save_counter(
        OUTPUT_DIR / "skill_triples.csv",
        ["skill_1", "skill_2", "skill_3", "vacancy_count"],
        triples_count,
    )

    elapsed = time.perf_counter() - start_time

    print("\n=== Результаты MapReduce ===")
    print(f"Обработано вакансий: {rows_processed}")
    print(f"Вакансий с навыками: {rows_with_skills}")
    print(f"Уникальных навыков: {len(skills_count)}")
    print(f"Уникальных пар: {len(pairs_count)}")
    print(f"Уникальных троек: {len(triples_count)}")
    print(f"Время выполнения: {elapsed:.3f} сек.")
    print(f"Результаты: {OUTPUT_DIR.resolve()}")

    print("\nТоп-15 навыков:")
    for skill, count in skills_count.most_common(15):
        print(f"{skill}: {count}")

    print("\nТоп-10 пар:")
    for (skill_1, skill_2), count in pairs_count.most_common(10):
        print(f"{skill_1} + {skill_2}: {count}")

    print("\nТоп-10 троек:")
    for (skill_1, skill_2, skill_3), count in triples_count.most_common(10):
        print(f"{skill_1} + {skill_2} + {skill_3}: {count}")


if __name__ == "__main__":
    main()
