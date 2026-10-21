import time
from pathlib import Path

import boto3
import duckdb


BUCKET = "hh-lake"
KEY = "java_developer_csv/java_vacancies.csv"
ENDPOINT = "http://localhost:9000"

ROOT = Path("results/duckdb")
SOURCE = ROOT / "java_vacancies.csv"
OUTPUT = ROOT / "sql"


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)

    # Получаем тот же исходный объект из RustFS.
    s3 = boto3.client("s3", endpoint_url=ENDPOINT)
    print(f"Скачиваем s3://{BUCKET}/{KEY}")
    s3.download_file(BUCKET, KEY, str(SOURCE))

    con = duckdb.connect()
    con.execute("SET threads = 1")

    source_sql = str(SOURCE.resolve()).replace("\\", "/").replace("'", "''")

    con.execute(f"""
        CREATE VIEW vacancies AS
        SELECT *
        FROM read_csv(
            '{source_sql}',
            header = true,
            all_varchar = true
        )
    """)

    # Одна строка на вакансию и уникальный нормализованный навык.
    con.execute("""
        CREATE TEMP VIEW vacancy_skills AS
        SELECT DISTINCT
            vacancy_id,
            lower(trim(skill)) AS skill
        FROM vacancies,
        UNNEST(string_split(coalesce(key_skills, ''), ';')) AS t(skill)
        WHERE trim(skill) <> ''
    """)

    queries = {
        "skills.csv": """
            SELECT skill, count(*) AS vacancy_count
            FROM vacancy_skills
            GROUP BY skill
            ORDER BY vacancy_count DESC, skill
        """,
        "skill_pairs.csv": """
            SELECT
                a.skill AS skill_1,
                b.skill AS skill_2,
                count(*) AS vacancy_count
            FROM vacancy_skills a
            JOIN vacancy_skills b
              ON a.vacancy_id = b.vacancy_id
             AND a.skill < b.skill
            GROUP BY a.skill, b.skill
            ORDER BY vacancy_count DESC, skill_1, skill_2
        """,
        "skill_triples.csv": """
            SELECT
                a.skill AS skill_1,
                b.skill AS skill_2,
                c.skill AS skill_3,
                count(*) AS vacancy_count
            FROM vacancy_skills a
            JOIN vacancy_skills b
              ON a.vacancy_id = b.vacancy_id
             AND a.skill < b.skill
            JOIN vacancy_skills c
              ON a.vacancy_id = c.vacancy_id
             AND b.skill < c.skill
            GROUP BY a.skill, b.skill, c.skill
            ORDER BY vacancy_count DESC, skill_1, skill_2, skill_3
        """,
    }

    started = time.perf_counter()

    for filename, query in queries.items():
        output_path = (OUTPUT / filename).resolve().as_posix()
        output_path = output_path.replace("'", "''")

        con.execute(f"""
            COPY ({query})
            TO '{output_path}'
            (HEADER, DELIMITER ',', QUOTE '"', ESCAPE '"')
        """)

        count = con.execute(f"SELECT count(*) FROM ({query}) AS result").fetchone()[0]
        print(f"{filename}: {count} комбинаций")

    print(f"Время SQL-подсчёта: {time.perf_counter() - started:.3f} сек.")
    print(f"Результаты DuckDB: {OUTPUT.resolve()}")

    con.close()


if __name__ == "__main__":
    main()

