from __future__ import annotations

import unittest

from wb_app.help_content import (
    OVERVIEW_HELP_CONTENT,
    REPORTS_HELP_CONTENT,
    help_plain_text,
)
from wb_app.ui import WBPriceAnalyzerApp


class HelpContentTests(unittest.TestCase):
    def test_reports_help_identifies_required_and_conditional_documents(self) -> None:
        text = help_plain_text(REPORTS_HELP_CONTENT)

        self.assertIn("Еженедельный детализированный отчёт — обязательный", text)
        self.assertIn("детализированный отчёт «по выкупам»", text)
        self.assertIn("Уведомление о выкупе XLSX", text)
        self.assertIn("загружаются парой", text)
        self.assertIn("Старый и новый форматы WB", text)
        self.assertIn("один день или несколько дней", text)

    def test_overview_help_documents_key_formulas(self) -> None:
        text = help_plain_text(OVERVIEW_HELP_CONTENT)

        self.assertIn("Выручка = Выручка MAIN + Выручка BUYOUT", text)
        self.assertIn(
            "Чистая прибыль товаров = Финрезультат товаров − С/с проданного − Налог",
            text,
        )
        self.assertIn(
            "Итог с нераспределёнными = Чистая прибыль товаров + Нераспределённые",
            text,
        )
        self.assertIn(
            "Доходность итога = Итог отчёта с нераспределёнными ÷ С/с проданного × 100%",
            text,
        )
        self.assertIn("Комиссия остаётся комиссией нетто", text)
        self.assertIn("Действует тот способ, который был использован последним", text)
        self.assertIn("«Исходные файлы»", text)
        self.assertIn("«Разбивка»", text)
        self.assertIn("«Сценарий цены»", text)

    def test_base_ui_exposes_help_tab_builder(self) -> None:
        self.assertTrue(callable(getattr(WBPriceAnalyzerApp, "_build_help_tab", None)))


if __name__ == "__main__":
    unittest.main()
