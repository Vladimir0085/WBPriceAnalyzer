from __future__ import annotations

import argparse
import os
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "docs" / "WBPriceAnalyzer_Instruction_v0.2.12.pdf"
VERSION = "0.2.12"

ACCENT = colors.HexColor("#C313A8")
ACCENT_DARK = colors.HexColor("#861174")
INK = colors.HexColor("#24222A")
MUTED = colors.HexColor("#66616C")
SURFACE = colors.HexColor("#F6F3F7")
SURFACE_STRONG = colors.HexColor("#EEE7F0")
SUCCESS = colors.HexColor("#21865A")
WARNING = colors.HexColor("#A86700")
WHITE = colors.white


def _register_fonts() -> tuple[str, str, str]:
    candidates = [
        (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
        ),
        (
            Path("/usr/local/share/fonts/dejavu/DejaVuSans.ttf"),
            Path("/usr/local/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
            Path("/usr/local/share/fonts/dejavu/DejaVuSansMono.ttf"),
        ),
        (
            Path.home() / ".fonts" / "DejaVuSans.ttf",
            Path.home() / ".fonts" / "DejaVuSans-Bold.ttf",
            Path.home() / ".fonts" / "DejaVuSansMono.ttf",
        ),
        (
            Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "arial.ttf",
            Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "arialbd.ttf",
            Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "consola.ttf",
        ),
    ]
    for regular, bold, mono in candidates:
        if regular.exists() and bold.exists() and mono.exists():
            pdfmetrics.registerFont(TTFont("GuideSans", str(regular)))
            pdfmetrics.registerFont(TTFont("GuideSans-Bold", str(bold)))
            pdfmetrics.registerFont(TTFont("GuideMono", str(mono)))
            return "GuideSans", "GuideSans-Bold", "GuideMono"
    raise FileNotFoundError(
        "DejaVu Sans fonts are required to generate the Russian PDF instruction"
    )


FONT, FONT_BOLD, FONT_MONO = _register_fonts()


def _clean(value: str) -> str:
    """Keep PDF text compatible and use only ASCII hyphens."""
    return (
        value.replace("\u2011", "-")
        .replace("\u2012", "-")
        .replace("\u2013", "-")
        .replace("\u2014", " - ")
        .replace("\u2212", "-")
    )


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=base["Title"],
            fontName=FONT_BOLD,
            fontSize=28,
            leading=33,
            textColor=INK,
            alignment=TA_LEFT,
            spaceAfter=10,
        ),
        "cover_subtitle": ParagraphStyle(
            "CoverSubtitle",
            parent=base["Normal"],
            fontName=FONT,
            fontSize=14,
            leading=20,
            textColor=MUTED,
            spaceAfter=18,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontName=FONT_BOLD,
            fontSize=19,
            leading=24,
            textColor=INK,
            spaceBefore=3,
            spaceAfter=11,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName=FONT_BOLD,
            fontSize=12.5,
            leading=16,
            textColor=ACCENT_DARK,
            spaceBefore=10,
            spaceAfter=6,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName=FONT,
            fontSize=9.5,
            leading=14,
            textColor=INK,
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["BodyText"],
            fontName=FONT,
            fontSize=8.2,
            leading=11.5,
            textColor=MUTED,
        ),
        "table": ParagraphStyle(
            "Table",
            parent=base["BodyText"],
            fontName=FONT,
            fontSize=8.1,
            leading=11.2,
            textColor=INK,
        ),
        "table_head": ParagraphStyle(
            "TableHead",
            parent=base["BodyText"],
            fontName=FONT_BOLD,
            fontSize=8.2,
            leading=10.5,
            textColor=WHITE,
            alignment=TA_CENTER,
        ),
        "callout_title": ParagraphStyle(
            "CalloutTitle",
            parent=base["BodyText"],
            fontName=FONT_BOLD,
            fontSize=9.2,
            leading=12,
            textColor=INK,
            spaceAfter=3,
        ),
        "callout": ParagraphStyle(
            "Callout",
            parent=base["BodyText"],
            fontName=FONT,
            fontSize=8.8,
            leading=12.5,
            textColor=INK,
        ),
        "formula": ParagraphStyle(
            "Formula",
            parent=base["BodyText"],
            fontName=FONT_MONO,
            fontSize=8.2,
            leading=12,
            textColor=INK,
        ),
        "footer": ParagraphStyle(
            "Footer",
            parent=base["BodyText"],
            fontName=FONT,
            fontSize=7.5,
            leading=9,
            textColor=MUTED,
        ),
    }


STYLES = _styles()


def p(text: str, style: str = "body") -> Paragraph:
    return Paragraph(_clean(text), STYLES[style])


def plain(text: str, style: str = "body") -> Paragraph:
    return p(escape(_clean(text)), style)


def bullet_list(items: list[str], *, level: int = 0) -> ListFlowable:
    return ListFlowable(
        [ListItem(plain(item), leftIndent=0) for item in items],
        bulletType="bullet",
        start="circle",
        leftIndent=(16 + level * 10) * mm,
        bulletFontName=FONT,
        bulletFontSize=7,
        bulletColor=ACCENT,
        spaceAfter=7,
    )


def numbered_list(items: list[str]) -> ListFlowable:
    return ListFlowable(
        [ListItem(plain(item), leftIndent=0) for item in items],
        bulletType="1",
        leftIndent=9 * mm,
        bulletFontName=FONT_BOLD,
        bulletFontSize=9,
        bulletColor=ACCENT_DARK,
        spaceAfter=7,
    )


def callout(title: str, text: str, *, color=ACCENT) -> Table:
    content = [
        plain(title, "callout_title"),
        plain(text, "callout"),
    ]
    table = Table([[content]], colWidths=[166 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), SURFACE),
                ("BOX", (0, 0), (-1, -1), 0.6, color),
                ("LINEBEFORE", (0, 0), (0, -1), 4, color),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    return table


def formula(text: str) -> Table:
    table = Table([[plain(text, "formula")]], colWidths=[166 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), SURFACE_STRONG),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8CDD9")),
                ("LEFTPADDING", (0, 0), (-1, -1), 11),
                ("RIGHTPADDING", (0, 0), (-1, -1), 11),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def data_table(headers: list[str], rows: list[list[str]], widths: list[float]) -> Table:
    data = [[plain(value, "table_head") for value in headers]]
    data.extend([[plain(value, "table") for value in row] for row in rows])
    table = Table(data, colWidths=[value * mm for value in widths], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), ACCENT_DARK),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D8D2DA")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, SURFACE]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def section_title(number: str, title: str) -> KeepTogether:
    badge = Table(
        [[plain(number, "table_head"), plain(title, "h1")]],
        colWidths=[13 * mm, 153 * mm],
        hAlign="LEFT",
    )
    badge.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), ACCENT),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (0, 0), 4),
                ("RIGHTPADDING", (0, 0), (0, 0), 4),
                ("TOPPADDING", (0, 0), (0, 0), 7),
                ("BOTTOMPADDING", (0, 0), (0, 0), 7),
                ("LEFTPADDING", (1, 0), (1, 0), 9),
                ("RIGHTPADDING", (1, 0), (1, 0), 0),
                ("TOPPADDING", (1, 0), (1, 0), 0),
                ("BOTTOMPADDING", (1, 0), (1, 0), 0),
            ]
        )
    )
    return KeepTogether([badge, Spacer(1, 4 * mm)])


def _cover(canvas, doc) -> None:
    width, height = A4
    canvas.saveState()
    canvas.setFillColor(ACCENT)
    canvas.rect(0, height - 18 * mm, width, 18 * mm, stroke=0, fill=1)
    canvas.setFillColor(ACCENT_DARK)
    canvas.rect(0, 0, width, 9 * mm, stroke=0, fill=1)
    canvas.restoreState()


def _later_page(canvas, doc) -> None:
    width, height = A4
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#DDD6DF"))
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, height - 13 * mm, width - 18 * mm, height - 13 * mm)
    canvas.setFont(FONT_BOLD, 7.5)
    canvas.setFillColor(ACCENT_DARK)
    canvas.drawString(18 * mm, height - 10 * mm, "WB PRICE ANALYZER")
    canvas.setFont(FONT, 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(width - 18 * mm, height - 10 * mm, f"Инструкция пользователя | v{VERSION}")
    canvas.line(18 * mm, 13 * mm, width - 18 * mm, 13 * mm)
    canvas.setFont(FONT, 7.5)
    canvas.drawString(18 * mm, 8.5 * mm, "Vladimir0085/WBPriceAnalyzer")
    canvas.drawRightString(width - 18 * mm, 8.5 * mm, f"Страница {doc.page}")
    canvas.restoreState()


def build_story() -> list[object]:
    story: list[object] = []

    story.extend(
        [
            Spacer(1, 26 * mm),
            p("WB PRICE ANALYZER", "cover_title"),
            p("Инструкция пользователя", "cover_subtitle"),
            HRFlowable(width="100%", thickness=2, color=ACCENT, spaceAfter=10 * mm),
            Table(
                [
                    [plain("Версия", "small"), plain(VERSION, "callout_title")],
                    [plain("Платформа", "small"), plain("Windows x64", "callout_title")],
                    [plain("Назначение", "small"), plain("Анализ детализированных финансовых отчётов Wildberries", "callout_title")],
                ],
                colWidths=[35 * mm, 125 * mm],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), SURFACE),
                        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#DDD6DF")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 9),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ]
                ),
            ),
            Spacer(1, 13 * mm),
            callout(
                "Главное в версии 0.2.12",
                "Артикулы из отчётов WB сопоставляются со справочником без учёта регистра. "
                "Например, ABC-123 и abc-123 считаются одним товаром; в результатах "
                "сохраняется написание из справочника.",
            ),
            Spacer(1, 27 * mm),
            plain("Актуально на 18.09.2026", "small"),
            plain("Формулы финансового результата и комиссия нетто не изменены.", "small"),
            PageBreak(),
        ]
    )

    story.extend(
        [
            section_title("1", "Быстрый старт"),
            p("Программа работает локально и не отправляет финансовые отчёты во внешние сервисы. "
              "Для работы не нужны Python и Microsoft Excel."),
            p("Порядок запуска", "h2"),
            numbered_list(
                [
                    "Скачайте Windows ZIP и полностью распакуйте его в отдельную папку.",
                    "Запустите WBPriceAnalyzer.exe. Повторный запуск развернёт уже открытое окно, а не создаст второй экземпляр.",
                    "Откройте «Настройки», укажите налоговую ставку и загрузите справочник себестоимости XLSX.",
                    "Нажмите «Импортировать отчёты» и выберите все связанные файлы одного расчёта одновременно.",
                    "Проверьте итоги в «Обзоре», а затем сохраните результат через «Экспорт в XLSX».",
                ]
            ),
            callout(
                "Где хранятся данные",
                r"База, история, настройки, копии отчётов и резервные копии хранятся отдельно от программы: %LOCALAPPDATA%\WBPriceAnalyzer. Замена папки с EXE не удаляет рабочие данные.",
                color=SUCCESS,
            ),
            p("Системные требования", "h2"),
            bullet_list(
                [
                    "Windows 10 или Windows 11, 64-разрядная система.",
                    "Доступ на запись в папку данных пользователя.",
                    "Исходные отчёты WB в формате XLSX без ручного переименования заголовков.",
                ]
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            section_title("2", "Какие документы WB загружать"),
            data_table(
                ["Документ", "Когда нужен", "Как используется"],
                [
                    [
                        "Еженедельный детализированный отчёт",
                        "Обязателен для каждого расчёта",
                        "Продажи, возвраты, выручка, выплата продавцу, логистика, штрафы, хранение, приёмка и прочие операции.",
                    ],
                    [
                        "Детализированный отчёт «по выкупам»",
                        "Если WB сформировал выкуп",
                        "Связанные расходы, корректировки и контроль цены выкупа. Сама выручка берётся из уведомления.",
                    ],
                    [
                        "Уведомление о выкупе XLSX",
                        "Обязательно для каждого отчёта «по выкупам»",
                        "Номер, дата, товары, количество и сумма выкупа. Номер должен совпадать с детализированным отчётом по выкупам.",
                    ],
                ],
                [47, 42, 77],
            ),
            Spacer(1, 5 * mm),
            callout(
                "Важно для выкупов",
                "Отчёт «по выкупам» и уведомление загружаются парой. Если одного файла нет или номера не совпадают, программа блокирует расчёт, чтобы не занизить выручку.",
                color=WARNING,
            ),
            p("Старый и новый форматы WB", "h2"),
            p("Программа автоматически распознаёт оба формата детализированного отчёта. Переименованные WB столбцы видов доставки, перемещения, операционной обработки и коэффициента логистики сопоставляются с внутренней схемой."),
            p("Коэффициент логистики считается справочным: денежная сумма логистики уже содержит его влияние и не пересчитывается повторно."),
            p("Как определяется период", "h2"),
            p("Период равен минимальной и максимальной «Дате продажи» внутри преобладающей ISO-недели. Поэтому отчёт за один день показывает одну дату, а отчёт за несколько дней не растягивается до полной недели."),
            callout(
                "Корректировки соседней недели",
                "Строки с датой другой недели участвуют в финансовом результате, но помечаются в «Контроле качества». Несколько самостоятельных основных отчётов за разные части одной недели хранятся отдельно.",
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            section_title("3", "Импорт и контроль качества"),
            p("При импорте можно выбрать файлы сразу за несколько периодов. Программа разделит их на самостоятельные расчёты по номерам, типам и фактическим периодам."),
            p("Что проверяет программа", "h2"),
            data_table(
                ["Проверка", "Реакция"],
                [
                    ["Нет основного детализированного отчёта", "Импорт блокируется."],
                    ["Нет уведомления для отчёта по выкупам", "Импорт блокируется до добавления парного файла."],
                    ["Файл уже загружался", "Предлагается безопасная замена отчёта за тот же период; двойной учёт не допускается."],
                    ["WB добавил неизвестные столбцы", "Файл не отклоняется автоматически. Список столбцов показывается для ручной проверки."],
                    ["Есть строки другой ISO-недели", "Строки учитываются как корректировки и отмечаются предупреждением."],
                    ["Новый артикул", "Сопоставление со справочником выполняется без учёта регистра. Если совпадения нет, товар нужно создать или явно пропустить."],
                ],
                [62, 104],
            ),
            p("После импорта", "h2"),
            bullet_list(
                [
                    "Откройте «Контроль качества» в истории отчёта и проверьте предупреждения.",
                    "Сверьте количество исходных файлов и фактический период.",
                    "Если история создана в старой версии, нажмите «Пересчитать историю» в «Настройках», чтобы уточнить неполные периоды.",
                ]
            ),
            callout(
                "Что не нужно выбирать",
                "УПД, УКД, счета-фактуры, акты, PDF, XML, банковские выписки и скриншоты не входят в расчёт. Справочник себестоимости загружается отдельно в «Настройках».",
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            section_title("4", "Выбор отчётов и синхронизация вкладок"),
            callout(
                "Правило приоритета",
                "Действует тот способ выбора, который был использован последним. Верхний список включает один отчёт. Кнопка «Выбрать отчёты…» включает отмеченный набор.",
                color=SUCCESS,
            ),
            Spacer(1, 5 * mm),
            data_table(
                ["Действие", "Активный набор", "Результат"],
                [
                    ["Выбрать строку в верхнем списке", "Один отчёт", "Прежний множественный выбор отменяется."],
                    ["Нажать «Выбрать отчёты…» и подтвердить", "Все отмеченные отчёты", "Показатели объединяются за весь выбранный период."],
                    ["Оставить в окне один отчёт", "Один отчёт", "Сценарий цены показывает и сохраняет его плановые цены."],
                ],
                [55, 43, 68],
            ),
            p("Какие вкладки используют активный набор", "h2"),
            data_table(
                ["Вкладка", "Данные при выборе нескольких отчётов"],
                [
                    ["Обзор", "Сводные карточки, товарная таблица, категории, налог и историческая себестоимость."],
                    ["Исходные файлы", "Файлы всех выбранных отчётов с типом, строками, суммой, периодом и SHA-256."],
                    ["Разбивка", "Объединённые нераспределённые доходы и расходы без артикула."],
                    ["Сценарий цены", "Сводные текущие и плановые показатели. Изменение плановых цен блокируется, пока выбрано более одного отчёта."],
                ],
                [45, 121],
            ),
            p("Пример", "h2"),
            numbered_list(
                [
                    "Вы отметили три отчёта через «Выбрать отчёты…». Четыре связанные вкладки показывают сумму этих трёх отчётов.",
                    "Затем вы выбрали один отчёт в верхнем списке. Все четыре вкладки сразу переключаются на него.",
                ]
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            section_title("5", "Показатели вкладки «Обзор»"),
            p("Общие карточки считаются по всему активному набору. Поиск, фильтр категории и сортировка таблицы не меняют общие итоги."),
            p("Каналы выручки", "h2"),
            formula("Общая выручка = Выручка MAIN + Выручка BUYOUT"),
            Spacer(1, 2 * mm),
            bullet_list(
                [
                    "MAIN - основные продажи по столбцу «Вайлдберриз реализовал Товар (Пр)» с учётом возвратов.",
                    "BUYOUT - сумма и количество товарных строк уведомления о выкупе.",
                    "Общее количество = продажи MAIN - возвраты MAIN + BUYOUT.",
                ]
            ),
            p("Финансовый результат", "h2"),
            formula("Чистая прибыль товара = Финрезультат WB - С/с проданного - Налог"),
            Spacer(1, 2 * mm),
            formula("Доходность товаров = Чистая прибыль товаров / С/с проданного x 100%"),
            Spacer(1, 2 * mm),
            p("Столбец «К перечислению Продавцу за реализованный Товар» уже учитывает комиссию WB и платёжные услуги. Поэтому комиссия, эквайринг и ПВЗ показываются справочно и не вычитаются второй раз."),
            callout(
                "Комиссия нетто и компенсация лояльности",
                "Комиссия остаётся комиссией нетто по данным WB. Компенсация скидки программы лояльности показывается аналитически, но не прибавляется повторно.",
                color=WARNING,
            ),
            p("Нераспределённые операции", "h2"),
            formula("Итог отчёта = Чистая прибыль товаров + Нераспределённые доходы и расходы"),
            Spacer(1, 2 * mm),
            formula("Доходность итога = Итог отчёта / С/с проданного x 100%"),
            p("Строки без артикула не распределяются искусственно между товарами. Они показываются в отдельной карточке и во вкладке «Разбивка»."),
            PageBreak(),
        ]
    )

    story.extend(
        [
            section_title("6", "Карточки, проценты и товарная таблица"),
            p("Карточки верхнего блока", "h2"),
            data_table(
                ["Показатель", "Содержание"],
                [
                    ["Выручка", "Товарная выручка MAIN + BUYOUT."],
                    ["Чистая прибыль", "Прибыль товаров без общих операций без артикула."],
                    ["Доходность", "Чистая прибыль товаров / себестоимость проданного."],
                    ["Продажи, шт.", "Количество MAIN и BUYOUT с учётом возвратов MAIN."],
                    ["Нераспределённые", "Сумма финансового результа строк без артикула."],
                    ["Исходные файлы", "Количество XLSX в активном наборе."],
                    ["Итог с нераспределёнными", "Прибыль всего отчёта и её доходность относительно с/с проданного."],
                ],
                [57, 109],
            ),
            p("Показатели относительно выручки", "h2"),
            formula("Комиссия WB, % = Комиссия нетто / Общая выручка x 100%"),
            Spacer(1, 1.5 * mm),
            formula("Логистика, % = Логистика / Общая выручка x 100%"),
            Spacer(1, 1.5 * mm),
            formula("Баллы, % = Лояльность и баллы / Общая выручка x 100%"),
            Spacer(1, 1.5 * mm),
            formula("Чистая прибыль, % от выручки = Итог отчёта / Общая выручка x 100%"),
            p("Итоги выбранной категории", "h2"),
            p("Блок категории суммирует только товары текущей категории. Нераспределённые операции не имеют категории и в этот блок не входят."),
            p("Товарная таблица", "h2"),
            bullet_list(
                [
                    "Средняя цена = рыночная выручка / количество продаж.",
                    "Финрезультат на единицу = финрезультат товара / количество продаж.",
                    "Чистая прибыль на единицу = чистая прибыль товара / количество продаж.",
                    "Доходность товара = чистая прибыль товара / с/с проданного товара.",
                    "Кнопка «Настроить столбцы…» изменяет видимость и порядок столбцов; настройка сохраняется.",
                ]
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            section_title("7", "Вкладки и основные рабочие сценарии"),
            data_table(
                ["Вкладка", "Назначение"],
                [
                    ["Обзор", "Итоговые карточки, категории, фильтры и товарная детализация."],
                    ["Исходные файлы", "Просмотр входящих XLSX без запуска Excel, включая поиск по показанным строкам."],
                    ["Разбивка", "Операции без артикула: количество строк, сумма и доля в нераспределённых."],
                    ["Справочник операций", "Правила распределения операций и статистика с артикулом и без артикула."],
                    ["Сценарий цены", "Прогноз выручки и прибыли при изменении цены и неизменном объёме продаж."],
                    ["История отчётов", "Сохранённые расчёты, периоды, контроль качества, переименование и удаление."],
                    ["Динамика", "График по выручке, прибыли, доходности, продажам и процентным метрикам с выбором годов."],
                    ["Сравнение периодов", "Сравнение двух сохранённых периодов по общим и товарным показателям."],
                    ["Справочник себестоимости", "Артикулы, названия, категории, материалы, трудозатраты и полная себестоимость."],
                    ["Справка", "Комплект документов WB, правила периода и формулы «Обзора»."],
                    ["Настройки", "Налоговая ставка, тема, каталог, пересчёт истории, резервные копии и папка данных."],
                ],
                [51, 115],
            ),
            p("Сценарий цены", "h2"),
            bullet_list(
                [
                    "Объём продаж остаётся равным фактическому объёму выбранного периода.",
                    "Доля перечисления продавцу берётся из выбранного периода; логистика и другие фиксированные затраты сохраняются.",
                    "Для набора отчётов показывается сводный сценарий без записи цен. Для редактирования выберите один отчёт.",
                ]
            ),
            p("Фильтры и размер таблиц", "h2"),
            p("Категория, артикул, метрика сортировки и направление применяются к таблице. Горизонтальный разделитель на вкладках «Обзор», «Сценарий цены» и «Настройки» можно перетаскивать, чтобы менять высоту таблицы."),
            PageBreak(),
        ]
    )

    story.extend(
        [
            section_title("8", "Справочник, экспорт и резервные копии"),
            p("Справочник себестоимости", "h2"),
            bullet_list(
                [
                    "Минимальные данные: артикул, название и полная себестоимость.",
                    "Регистр букв не влияет на сопоставление с отчётами WB; написание из справочника используется в результатах.",
                    "Можно указать материал, трудозатраты и категорию. Материал + трудозатраты должны совпадать с полной с/с.",
                    "Строки без полной с/с не участвуют в расчёте, пока значение не будет заполнено.",
                    "Изменение каталога не переписывает историческую с/с без явного пересчёта истории.",
                ]
            ),
            p("Экспорт в XLSX", "h2"),
            p("Экспорт создаёт книгу с листами «Итог», «Разбивка» и «Справочник операций». Процентные метрики, доходность итога и нераспределённые операции переносятся в файл."),
            callout(
                "Экспорт объединённого обзора",
                "Если на вкладке «Обзор» активен набор отчётов, экспорт из этой вкладки создаст сводную книгу за весь выбранный период.",
            ),
            p("Резервные копии", "h2"),
            numbered_list(
                [
                    "Перед переносом на другой компьютер откройте «Настройки» и создайте файл резервной копии.",
                    "Скопируйте файл .wbbackup на новый компьютер.",
                    "Установите новую сборку, запустите её и восстановите копию через «Настройки».",
                ]
            ),
            p("Обновление программы", "h2"),
            bullet_list(
                [
                    "Закройте программу и распакуйте новую сборку в новую папку.",
                    "Рабочие данные останутся в %LOCALAPPDATA% и будут открыты новой версией.",
                    "Перед крупным обновлением создайте резервную копию.",
                ]
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            section_title("9", "Решение типовых проблем"),
            data_table(
                ["Ситуация", "Что делать"],
                [
                    ["Программа не видит обязательный столбец", "Убедитесь, что загружен исходный XLSX, а не PDF и не изменённая копия. Текущая версия поддерживает старые и новые заголовки WB."],
                    ["Артикул отличается только регистром", "Исправлять отчёт WB не нужно: ABC-123 и abc-123 сопоставляются как один товар. Если такие варианты одновременно заведены в справочнике, оставьте один."],
                    ["Дата отчёта не равна полной неделе", "Это нормально: период берётся по фактическим датам продажи. Для старой истории выполните «Пересчитать историю»."],
                    ["После выбора нескольких отчётов не удаётся изменить цену", "Сводный сценарий предназначен для просмотра. Выберите один отчёт в верхнем списке или оставьте одну отметку в окне выбора."],
                    ["Нет доходности или показано «Нет продаж»", "Без продаж или себестоимости знаменатель доходности отсутствует. Проверьте количество продаж и каталог."],
                    ["Выручка выкупа неполная", "Проверьте наличие уведомления XLSX с тем же номером, что и отчёт «по выкупам»."],
                    ["Windows показывает «Неизвестный издатель»", "Сверьте источник архива. До подключения сертифика тестовые сборки могут не иметь цифровой подписи."],
                ],
                [59, 107],
            ),
            p("Что приложить к сообщению об ошибке", "h2"),
            bullet_list(
                [
                    "Скриншот окна с ошибкой и видимый номер версии.",
                    "Исходные XLSX, на которых возникла проблема.",
                    "Ожидаемый результат и конкретный показатель, который не совпал.",
                ]
            ),
            callout(
                "Репозиторий и сборки",
                "Исходный код и Windows-сборки: https://github.com/Vladimir0085/WBPriceAnalyzer",
                color=SUCCESS,
            ),
            Spacer(1, 8 * mm),
            HRFlowable(width="100%", thickness=1, color=colors.HexColor("#DDD6DF"), spaceAfter=5 * mm),
            p("Краткая памятка", "h2"),
            numbered_list(
                [
                    "Заполните справочник с/с.",
                    "Загрузите все связанные файлы WB одновременно.",
                    "Проверьте фактический период и контроль качества.",
                    "Выберите один отчёт или набор. Последний способ выбора имеет приоритет.",
                    "Сверьте «Обзор», «Исходные файлы», «Разбивку» и «Сценарий цены».",
                    "Создайте экспорт XLSX и резервную копию.",
                ]
            ),
        ]
    )
    return story


def generate(output: Path) -> Path:
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        rightMargin=22 * mm,
        leftMargin=22 * mm,
        topMargin=19 * mm,
        bottomMargin=18 * mm,
        title=f"WB Price Analyzer {VERSION} - Инструкция пользователя",
        author="otdelvsego-spec",
        subject="Инструкция по WB Price Analyzer для Windows",
        creator="WB Price Analyzer",
    )
    document.build(build_story(), onFirstPage=_cover, onLaterPages=_later_page)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the WB Price Analyzer PDF guide")
    parser.add_argument("output", nargs="?", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(generate(args.output))


if __name__ == "__main__":
    main()
