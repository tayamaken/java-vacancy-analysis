import csv
import html
from pathlib import Path
from datetime import date

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether
)

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUT_DIR = ROOT / "reports"
OUT_FILE = OUT_DIR / "java_vacancy_analysis_report.pdf"

FONT = Path(r"C:\Windows\Fonts\arial.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\arialbd.ttf")

if not FONT.exists():
    raise FileNotFoundError(f"Не найден шрифт: {FONT}")
if not FONT_BOLD.exists():
    FONT_BOLD = FONT

pdfmetrics.registerFont(TTFont("Arial", str(FONT)))
pdfmetrics.registerFont(TTFont("Arial-Bold", str(FONT_BOLD)))

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name="ReportTitle", fontName="Arial-Bold", fontSize=22,
    leading=28, alignment=TA_CENTER, textColor=colors.HexColor("#17365D"),
    spaceAfter=12
))
styles.add(ParagraphStyle(
    name="Section", fontName="Arial-Bold", fontSize=15,
    leading=19, textColor=colors.HexColor("#17365D"),
    spaceBefore=12, spaceAfter=8, keepWithNext=True
))
styles.add(ParagraphStyle(
    name="Subsection", fontName="Arial-Bold", fontSize=11,
    leading=14, spaceBefore=8, spaceAfter=5, keepWithNext=True
))
styles.add(ParagraphStyle(
    name="BodyRu", fontName="Arial", fontSize=9,
    leading=13, spaceAfter=6
))
styles.add(ParagraphStyle(
    name="SmallRu", fontName="Arial", fontSize=7,
    leading=9, spaceAfter=3
))
styles.add(ParagraphStyle(
    name="CellRu", fontName="Arial", fontSize=6.5,
    leading=8, wordWrap="CJK"
))
styles.add(ParagraphStyle(
    name="CellHeaderRu", fontName="Arial-Bold", fontSize=6.5,
    leading=8, textColor=colors.white, wordWrap="CJK"
))


def read_csv(relative_path):
    path = RESULTS / relative_path
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return reader.fieldnames or [], rows


def fmt(value):
    value = "" if value is None else str(value)
    if len(value) > 90:
        value = value[:87] + "..."
    return html.escape(value).replace("\n", " ")


def add_table(story, headers, rows, max_rows=12):
    if not headers:
        story.append(Paragraph("Файл отсутствует или не содержит заголовков.", styles["BodyRu"]))
        return

    # Слишком широкие таблицы сокращаем до первых шести столбцов.
    shown_headers = headers[:6]
    omitted = len(headers) - len(shown_headers)

    data = [[Paragraph(fmt(h), styles["CellHeaderRu"]) for h in shown_headers]]
    for row in rows[:max_rows]:
        data.append([
            Paragraph(fmt(row.get(h, "")), styles["CellRu"])
            for h in shown_headers
        ])

    if len(rows) > max_rows:
        data.append([
            Paragraph(
                f"Показаны первые {max_rows} из {len(rows)} строк.",
                styles["CellRu"]
            )
        ] + [Paragraph("", styles["CellRu"]) for _ in shown_headers[1:]])

    if omitted:
        story.append(Paragraph(
            f"Примечание: показаны первые шесть столбцов из {len(headers)}.",
            styles["SmallRu"]
        ))

    usable_width = A4[0] - 34 * mm
    col_widths = [usable_width / len(shown_headers)] * len(shown_headers)
    table = Table(data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#24476B")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C8D2DC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#F0F4F8")]),
    ]))
    story.append(table)
    story.append(Spacer(1, 5 * mm))


def add_csv_section(story, title, relative_path, max_rows=10, description=None):
    story.append(Paragraph(title, styles["Subsection"]))
    if description:
        story.append(Paragraph(description, styles["BodyRu"]))
    headers, rows = read_csv(relative_path)
    if not headers:
        story.append(Paragraph(
            f"Не найден файл results/{relative_path}.",
            styles["BodyRu"]
        ))
    else:
        story.append(Paragraph(
            f"Источник: results/{relative_path}. Всего строк: {len(rows)}.",
            styles["SmallRu"]
        ))
        add_table(story, headers, rows, max_rows=max_rows)


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Arial", 8)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawString(17 * mm, 10 * mm, "Анализ вакансий Java-разработчиков")
    canvas.drawRightString(A4[0] - 17 * mm, 10 * mm, f"Страница {doc.page}")
    canvas.restoreState()


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    story = []

    story.append(Spacer(1, 28 * mm))
    story.append(Paragraph(
        "Анализ вакансий Java-разработчиков",
        styles["ReportTitle"]
    ))
    story.append(Paragraph(
        "Обработка данных с использованием RustFS, MapReduce и DuckDB",
        ParagraphStyle(
            "Subtitle", parent=styles["BodyRu"], alignment=TA_CENTER,
            fontSize=12, leading=17
        )
    ))
    story.append(Spacer(1, 12 * mm))
    story.append(Paragraph(
        f"Отчёт подготовлен {date.today().strftime('%d.%m.%Y')}",
        ParagraphStyle("Date", parent=styles["BodyRu"], alignment=TA_CENTER)
    ))
    story.append(Spacer(1, 35 * mm))
    story.append(Paragraph(
        "Репозиторий: github.com/tayamaken/java-vacancy-analysis",
        ParagraphStyle("Repo", parent=styles["BodyRu"], alignment=TA_CENTER)
    ))
    story.append(PageBreak())

    story.append(Paragraph("1. Цель и данные", styles["Section"]))
    story.append(Paragraph(
        "Цель проекта — обработать вакансии Java-разработчиков, определить "
        "часто встречающиеся навыки и комбинации навыков, сравнить результаты "
        "двух независимых реализаций, оценить производительность чтения чанками "
        "и исследовать различия между регионами и зарплатными группами.",
        styles["BodyRu"]
    ))
    story.append(Paragraph(
        "Подготовленный набор содержит 6 907 вакансий. Подготовленный CSV "
        "занимает 25 775 271 байт (около 25,8 МБ). Исходный файл расположен "
        "локально по пути D:\\ITMO\\DataEng\\rustfs-data\\it_vacancies_2024.csv "
        "и занимает около 848 МБ. Исходные данные не включаются в Git.",
        styles["BodyRu"]
    ))

    story.append(Paragraph("2. Архитектура и хранение", styles["Section"]))
    story.append(Paragraph(
        "RustFS используется как S3-совместимое объектное хранилище. "
        "Endpoint: http://localhost:9000, bucket: hh-lake. Подготовленный "
        "набор хранится по ключу java_developer_csv/java_vacancies.csv. "
        "Результаты MapReduce размещаются под префиксом mapreduce_chunked/.",
        styles["BodyRu"]
    ))
    story.append(Paragraph(
        "Основные компоненты проекта: src/mapreduce_chunked.py — MapReduce "
        "с чтением чанками; src/duckdb_analysis.py — независимый SQL-подсчёт; "
        "src/compare_results.py — сравнение; отдельные скрипты отвечают "
        "за зарплаты и региональные срезы. Локальные таблицы находятся "
        "в каталоге results/.",
        styles["BodyRu"]
    ))

    story.append(Paragraph("3. Результаты MapReduce", styles["Section"]))
    story.append(Paragraph(
        "Обработка выполнена с размерами чанков 256 КБ, 1 МБ и 4 МБ. "
        "Во всех вариантах обработано 6 907 вакансий. Получены 1 343 "
        "уникальных навыка, 20 635 уникальных пар и 137 489 уникальных троек. "
        "Число троек существенно больше числа навыков, поскольку комбинации "
        "могут составляться из множества разных сочетаний навыков одной вакансии.",
        styles["BodyRu"]
    ))
    add_csv_section(
        story, "Сводка MapReduce", "mapreduce_chunked/profiling.csv",
        max_rows=15
    )
    add_csv_section(
        story, "Пример результата: навыки", "mapreduce_chunked/256KB/skills.csv",
        max_rows=10
    )
    add_csv_section(
        story, "Пример результата: пары навыков",
        "mapreduce_chunked/256KB/skill_pairs.csv", max_rows=8
    )
    add_csv_section(
        story, "Пример результата: тройки навыков",
        "mapreduce_chunked/256KB/skill_triples.csv", max_rows=8
    )

    story.append(Paragraph("4. Проверка через DuckDB", styles["Section"]))
    story.append(Paragraph(
        "Для проверки корректности выполнен независимый подсчёт с помощью "
        "DuckDB и SQL. Скрипт compare_results.py сравнил CSV MapReduce "
        "и DuckDB. Во всех трёх наборах не обнаружено различий ни по составу "
        "строк, ни по частотам.",
        styles["BodyRu"]
    ))
    headers, rows = read_csv("duckdb/sql/skills.csv")
    story.append(Paragraph("Пример SQL-результата", styles["Subsection"]))
    add_table(story, headers, rows, max_rows=8)
    story.append(Paragraph(
        "Проверенные размеры результатов: 1 343 навыка, 20 635 пар "
        "и 137 489 троек. Совпадение двух независимых реализаций является "
        "подтверждением корректности подсчёта на данном наборе данных.",
        styles["BodyRu"]
    ))

    story.append(Paragraph("5. Производительность", styles["Section"]))
    story.append(Paragraph(
        "Каждый размер чанка был измерен в трёх запусках. В таблице приведены "
        "сводные значения из profiling_summary.csv. Пиковая память отражает "
        "наблюдавшееся потребление памяти процесса в условиях этого эксперимента.",
        styles["BodyRu"]
    ))
    add_csv_section(
        story, "Сводная производительность",
        "mapreduce_chunked/profiling_summary.csv", max_rows=10
    )
    add_csv_section(
        story, "Девять повторных измерений",
        "mapreduce_chunked/profiling_repeated_measurements.csv", max_rows=12
    )
    story.append(Paragraph(
        "В проведённом эксперименте среднее время для чанка 256 КБ составило "
        "около 1,0344 с, для 1 МБ — 1,8260 с, для 4 МБ — 5,6643 с. "
        "Средняя пиковая память составила около 84,29; 84,63 и 86,46 МБ "
        "соответственно. Количество операций чтения уменьшалось с 99 до 25 "
        "и 7. Несмотря на меньшее число чтений, большие чанки оказались "
        "медленнее в данной реализации и среде. Этот результат нельзя "
        "обобщать на другие системы без дополнительных экспериментов.",
        styles["BodyRu"]
    ))

    story.append(PageBreak())
    story.append(Paragraph("6. Региональный анализ", styles["Section"]))
    story.append(Paragraph(
        "В региональном сравнении рассмотрены Москва, Санкт-Петербург "
        "и Новосибирск. Число вакансий составляет 3 376, 935 и 308 "
        "соответственно. Поэтому доли навыков в Новосибирске основаны "
        "на меньшей выборке и могут быть менее устойчивыми.",
        styles["BodyRu"]
    ))
    add_csv_section(
        story, "Навыки по регионам",
        "regions/skills_by_region.csv", max_rows=18
    )
    add_csv_section(
        story, "Зарплаты по регионам",
        "salary/salary_by_region.csv", max_rows=15
    )

    story.append(Paragraph("7. Качество зарплатных данных", styles["Section"]))
    story.append(Paragraph(
        "В 5 219 из 6 907 вакансий зарплата не указана (75,56%). "
        "Значения gross отсутствуют в 5 219 строках; 1 173 строки имеют "
        "gross=false, а 515 — gross=true. Поэтому анализ зарплат выполняется "
        "на подмножестве объявлений с доступными данными и не описывает "
        "весь рынок без смещения.",
        styles["BodyRu"]
    ))
    add_csv_section(
        story, "Качество зарплат",
        "salary/salary_quality.csv", max_rows=15
    )
    add_csv_section(
        story, "Распределение валют",
        "salary/salary_by_currency.csv", max_rows=10
    )
    add_csv_section(
        story, "Сводная статистика зарплат",
        "salary/salary_numeric_summary.csv", max_rows=15
    )
    add_csv_section(
        story, "Диапазоны зарплат",
        "salary/salary_ranges.csv", max_rows=12
    )

    story.append(Paragraph("8. Навыки и зарплата", styles["Section"]))
    story.append(Paragraph(
        "Для зарплатного анализа использовались вакансии с зарплатой в RUB "
        "и пригодными данными о навыках. Медианы для комбинаций навыков "
        "являются описательными ассоциациями: они не доказывают, что наличие "
        "конкретного навыка вызывает рост или снижение зарплаты. На результаты "
        "влияют уровень специалиста, регион, размер выборки, тип компании "
        "и полнота объявления. Малочисленные группы следует интерпретировать "
        "особенно осторожно.",
        styles["BodyRu"]
    ))
    add_csv_section(
        story, "Навыки и зарплаты",
        "salary/skill_combinations/skills_salary.csv", max_rows=12
    )
    add_csv_section(
        story, "Пары навыков и зарплаты",
        "salary/skill_combinations/pairs_salary.csv", max_rows=12
    )
    add_csv_section(
        story, "Тройки навыков и зарплаты",
        "salary/skill_combinations/triples_salary.csv", max_rows=12
    )

    story.append(Paragraph("9. Выводы и ограничения", styles["Section"]))
    conclusions = [
        "MapReduce позволил подсчитать частоты навыков, пар и троек при чтении данных чанками.",
        "Результаты MapReduce полностью совпали с независимым подсчётом DuckDB.",
        "В измерениях на этой машине чанки 256 КБ показали наименьшее среднее время, но это не универсальный вывод для любых данных и систем.",
        "Региональные результаты показывают различия в частоте упоминания навыков; размер выборки по регионам неодинаков.",
        "Большая доля вакансий не содержит зарплату. Зарплатные выводы основаны на неполном подмножестве и являются наблюдательными, а не причинными.",
        "Результаты зависят от качества исходных данных, нормализации названий навыков и выбранных параметров обработки."
    ]
    for item in conclusions:
        story.append(Paragraph("• " + html.escape(item), styles["BodyRu"]))

    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(
        "Код и результаты проекта: "
        "https://github.com/tayamaken/java-vacancy-analysis",
        styles["BodyRu"]
    ))

    doc = SimpleDocTemplate(
        str(OUT_FILE), pagesize=A4,
        rightMargin=17 * mm, leftMargin=17 * mm,
        topMargin=17 * mm, bottomMargin=17 * mm,
        title="Анализ вакансий Java-разработчиков",
        author="Учебный проект"
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(f"PDF создан: {OUT_FILE}")
    print(f"Размер файла: {OUT_FILE.stat().st_size:,} байт")


if __name__ == "__main__":
    main()
