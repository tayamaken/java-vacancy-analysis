import csv
import gc
import itertools
import threading
import time
from collections import Counter
from pathlib import Path
from typing import Iterator

import boto3
import psutil


BUCKET = "hh-lake"
SOURCE_KEY = "java_developer_csv/java_vacancies.csv"
S3_ENDPOINT = "http://localhost:9000"

CHUNK_SIZES = {
    "256KB": 256 * 1024,
    "1MB": 1024 * 1024,
    "4MB": 4 * 1024 * 1024,
}

LOCAL_ROOT = Path("results/mapreduce_chunked")
S3_ROOT = "mapreduce_chunked"


def iter_csv_lines(body, chunk_size: int, stats: dict) -> Iterator[str]:
    """Читает S3-поток блоками и выдаёт полные физические строки CSV."""
    import codecs

    decoder = codecs.getincrementaldecoder("utf-8-sig")()
    pending = ""

    while True:
        chunk = body.read(chunk_size)
        if not chunk:
            break

        stats["bytes_read"] += len(chunk)
        stats["read_chunks"] += 1
        pending += decoder.decode(chunk)

        # Разбиваем только по физическим переводам строк.
        # csv.DictReader самостоятельно обрабатывает поля с кавычками
        # и переводами строк внутри описания вакансии.
        while "\n" in pending:
            line, pending = pending.split("\n", 1)
            yield line + "\n"

    pending += decoder.decode(b"", final=True)
    if pending:
        yield pending


def normalize_skills(value: str) -> list[str]:
    """Нормализует регистр и убирает повторы внутри вакансии."""
    return sorted({
        skill.strip().casefold()
        for skill in (value or "").split(";")
        if skill.strip()
    })


def save_counter(path: Path, header: list[str], counter: Counter) -> None:
    """Сохраняет результаты по убыванию частоты."""
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


def profile_run(s3, label: str, chunk_size: int) -> dict:
    output_dir = LOCAL_ROOT / label
    output_dir.mkdir(parents=True, exist_ok=True)

    stats = {
        "bytes_read": 0,
        "read_chunks": 0,
    }

    skills_count = Counter()
    pairs_count = Counter()
    triples_count = Counter()

    rows_processed = 0
    rows_with_skills = 0
    process = psutil.Process()
    peak_rss = [process.memory_info().rss]
    stop_monitor = threading.Event()

    def monitor_memory():
        while not stop_monitor.wait(0.01):
            try:
                rss = process.memory_info().rss
                peak_rss[0] = max(peak_rss[0], rss)
            except psutil.Error:
                break

    monitor = threading.Thread(target=monitor_memory, daemon=True)
    started = time.perf_counter()
    monitor.start()

    try:
        response = s3.get_object(
            Bucket=BUCKET,
            Key=SOURCE_KEY,
        )
        body = response["Body"]

        try:
            reader = csv.DictReader(
                iter_csv_lines(body, chunk_size, stats)
            )

            if "key_skills" not in (reader.fieldnames or []):
                raise ValueError("В CSV отсутствует столбец key_skills")

            for row in reader:
                rows_processed += 1
                skills = normalize_skills(row.get("key_skills", ""))

                if not skills:
                    continue

                rows_with_skills += 1
                skills_count.update(skills)
                pairs_count.update(itertools.combinations(skills, 2))
                triples_count.update(itertools.combinations(skills, 3))
        finally:
            body.close()

        save_counter(
            output_dir / "skills.csv",
            ["skill", "vacancy_count"],
            skills_count,
        )
        save_counter(
            output_dir / "skill_pairs.csv",
            ["skill_1", "skill_2", "vacancy_count"],
            pairs_count,
        )
        save_counter(
            output_dir / "skill_triples.csv",
            ["skill_1", "skill_2", "skill_3", "vacancy_count"],
            triples_count,
        )

        # Сохраняем результаты каждого размера чанка в RustFS.
        for filename in (
            "skills.csv",
            "skill_pairs.csv",
            "skill_triples.csv",
        ):
            s3.upload_file(
                str(output_dir / filename),
                BUCKET,
                f"{S3_ROOT}/{label}/{filename}",
            )
    finally:
        stop_monitor.set()
        monitor.join()
        elapsed = time.perf_counter() - started

    peak_rss[0] = max(peak_rss[0], process.memory_info().rss)

    result = {
        "chunk_size": label,
        "chunk_bytes": chunk_size,
        "rows_processed": rows_processed,
        "rows_with_skills": rows_with_skills,
        "unique_skills": len(skills_count),
        "unique_pairs": len(pairs_count),
        "unique_triples": len(triples_count),
        "bytes_read": stats["bytes_read"],
        "read_chunks": stats["read_chunks"],
        "elapsed_seconds": round(elapsed, 4),
        "peak_rss_mb": round(peak_rss[0] / (1024 * 1024), 2),
    }

    print(f"\n=== Чанк {label} ===")
    for key, value in result.items():
        print(f"{key}: {value}")

    del skills_count, pairs_count, triples_count
    gc.collect()

    return result


def main() -> None:
    s3 = boto3.client("s3", endpoint_url=S3_ENDPOINT)

    LOCAL_ROOT.mkdir(parents=True, exist_ok=True)
    measurements = []

    for label, chunk_size in CHUNK_SIZES.items():
        measurements.append(profile_run(s3, label, chunk_size))

    report_path = LOCAL_ROOT / "profiling.csv"
    with report_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(measurements[0].keys()),
        )
        writer.writeheader()
        writer.writerows(measurements)

    s3.upload_file(
        str(report_path),
        BUCKET,
        f"{S3_ROOT}/profiling.csv",
    )

    print("\n=== Сравнение размеров чанков ===")
    for row in measurements:
        print(
            f"{row['chunk_size']}: "
            f"{row['elapsed_seconds']} сек., "
            f"пик RSS {row['peak_rss_mb']} МБ, "
            f"прочитано блоков {row['read_chunks']}"
        )

    print(f"\nЛокальные результаты: {LOCAL_ROOT.resolve()}")
    print(f"S3: s3://{BUCKET}/{S3_ROOT}/")


if __name__ == "__main__":
    main()
