"""Interface changes of 0.2.16 (aligned with OZ Price Analyzer 0.5.31), synthetic data only."""

from __future__ import annotations

import os
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

from wb_app.help_content import (
    CATEGORY_CARD_HELP,
    COMMISSION_REFERENCE_NOTE,
    NO_UNALLOCATED_TAX_NOTE,
    OVERVIEW_CARD_HELP,
    OVERVIEW_HELP_CONTENT,
    REVENUE_SHARE_CARD_HELP,
    card_tooltip_text,
    help_plain_text,
)
from wb_app.models import RunSummary
from wb_app.report_totals import POINTS_CARD_TITLE, ReportTotalsWBPriceAnalyzerApp
from wb_app.ui import (
    report_name_is_custom,
    run_full_display,
    run_header_display,
    run_tooltip_text,
)
from wb_app.ui_layout import DisplayWBPriceAnalyzerApp
from tests.test_calculation_etalon import import_synthetic_reports


def _run(run_id: int, name: str, start: str | None, end: str | None) -> RunSummary:
    return RunSummary(
        id=run_id,
        created_at="2026-09-21T10:00:00",
        period_start=start,
        period_end=end,
        source_count=1,
        units=0,
        revenue=0,
        net_profit=0,
        unallocated_total=0,
        status="Готов",
        report_name=name,
    )


class ReportListLabelTests(unittest.TestCase):
    def test_generated_name_is_shown_as_compact_period(self) -> None:
        run = _run(7, "Отчет Wildberries за 14.09.2026–20.09.2026", "2026-09-14", "2026-09-20")
        self.assertFalse(report_name_is_custom(run))
        self.assertEqual(run_header_display(4, run), "№4 · 14.09–20.09.2026")

    def test_single_day_and_legacy_names(self) -> None:
        single = _run(3, "Отчет Wildberries за 31.08.2026", "2026-08-31", "2026-08-31")
        self.assertEqual(run_header_display(2, single), "№2 · 31.08.2026")
        legacy = _run(5, "Отчет Wildberries #5", "2026-09-14", "2026-09-20")
        self.assertFalse(report_name_is_custom(legacy))
        self.assertEqual(run_header_display(3, legacy), "№3 · 14.09–20.09.2026")

    def test_renamed_report_keeps_its_name(self) -> None:
        run = _run(7, "Неделя 38 — проверено", "2026-09-14", "2026-09-20")
        self.assertTrue(report_name_is_custom(run))
        self.assertEqual(run_header_display(4, run), "№4 · Неделя 38 — проверено")

    def test_period_across_years_and_missing_period(self) -> None:
        crossing = _run(3, "Отчет Wildberries за 29.12.2025–04.01.2026", "2025-12-29", "2026-01-04")
        self.assertEqual(run_header_display(1, crossing), "№1 · 29.12.2025–04.01.2026")
        missing = _run(5, "Отчет Wildberries без периода", None, None)
        self.assertEqual(run_header_display(2, missing), "№2 · Период не определен")

    def test_tooltip_and_comparison_list_keep_the_full_name(self) -> None:
        run = _run(7, "Отчет Wildberries за 14.09.2026–20.09.2026", "2026-09-14", "2026-09-20")
        self.assertEqual(
            run_tooltip_text(4, run),
            "Отчет №4: Отчет Wildberries за 14.09.2026–20.09.2026\nПериод: 14.09.2026–20.09.2026",
        )
        self.assertEqual(
            run_full_display(4, run),
            "№4 · Отчет Wildberries за 14.09.2026–20.09.2026 · 14.09.2026–20.09.2026",
        )


class HelpAndCardTextTests(unittest.TestCase):
    def test_every_card_tooltip_formula_is_printed_in_help(self) -> None:
        text = help_plain_text(OVERVIEW_HELP_CONTENT)
        for group in (OVERVIEW_CARD_HELP, REVENUE_SHARE_CARD_HELP, CATEGORY_CARD_HELP):
            for key, card_help in group.items():
                with self.subTest(card=key):
                    formulas, _note = card_help
                    self.assertTrue(formulas)
                    for formula in formulas:
                        self.assertIn(formula, text)
                        self.assertIn(formula, card_tooltip_text(card_help))

    def test_activity_profit_tooltip_states_no_unallocated_tax(self) -> None:
        tooltip = card_tooltip_text(OVERVIEW_CARD_HELP["report_total"])
        self.assertIn("Налог с нераспределённых операций не начисляется", tooltip)
        self.assertIn("Выручка MAIN + Выручка BUYOUT", tooltip)
        self.assertIn(NO_UNALLOCATED_TAX_NOTE, help_plain_text(OVERVIEW_HELP_CONTENT))

    def test_commission_tooltip_is_reference_only(self) -> None:
        tooltip = card_tooltip_text(REVENUE_SHARE_CARD_HELP["commission"])
        self.assertIn("Справочно", tooltip)
        self.assertIn("уже учтена в сумме «К перечислению продавцу»", tooltip)
        self.assertIn(COMMISSION_REFERENCE_NOTE, help_plain_text(OVERVIEW_HELP_CONTENT))

    def test_loyalty_card_is_an_expense(self) -> None:
        self.assertEqual(POINTS_CARD_TITLE, "Лояльность и баллы (расход)")
        text = help_plain_text(OVERVIEW_HELP_CONTENT)
        self.assertIn("Лояльность и баллы (расход), % =", text)
        self.assertNotIn("Баллы, % = ", text)
        self.assertIn("расход программы лояльности", card_tooltip_text(REVENUE_SHARE_CARD_HELP["points"]))

    def test_help_describes_short_report_names_and_tooltips(self) -> None:
        text = help_plain_text(OVERVIEW_HELP_CONTENT)
        self.assertIn("«№4 · 14.09–20.09.2026»", text)
        self.assertIn("Наведите указатель на любую карточку", text)


class InterfaceTkTests(unittest.TestCase):
    """Real Tk geometry; runs on Windows CI and under Xvfb, skipped without a display."""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            probe = tk.Tk()
        except tk.TclError as exc:
            if "no display name" in str(exc) or "couldn't connect to display" in str(exc):
                raise unittest.SkipTest(f"Tk display is unavailable: {exc}") from exc
            raise
        probe.destroy()

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        env_patch = patch.dict(os.environ, {"WB_APP_DATA": str(root / "app")})
        env_patch.start()
        self.addCleanup(env_patch.stop)
        service = import_synthetic_reports(root)
        self.first_id, self.second_id = [run.id for run in service.db.list_runs()]
        service.db.rename_run(self.first_id, "Неделя 37 — проверено")

        self.callback_errors: list[tuple[object, ...]] = []
        error_patch = patch(
            "tkinter.Tk.report_callback_exception",
            side_effect=lambda *error: self.callback_errors.append(error),
        )
        error_patch.start()
        self.addCleanup(error_patch.stop)
        initialize_tk = tk.Tk.__init__

        def initialize_at_test_dpi(tk_root, *args, **kwargs):
            initialize_tk(tk_root, *args, **kwargs)
            tk_root.tk.call("tk", "scaling", 96 / 72)

        with patch("tkinter.Tk.__init__", initialize_at_test_dpi), patch.object(
            DisplayWBPriceAnalyzerApp, "_maximize_on_small_screen", lambda self: None
        ):
            self.app = ReportTotalsWBPriceAnalyzerApp(service)
        self.addCleanup(self.app.destroy)
        self.app.minsize(1, 1)
        self.app.maxsize(2200, 1400)
        self.app._base_tk_scaling = 96 / 72
        self.app._apply_ui_scale(1.0)

    def settle(self) -> None:
        for _ in range(4):
            self.app.update_idletasks()
            self.app.update()
        self.assertEqual(self.callback_errors, [])

    def assert_inside(self, child, parent) -> None:
        self.assertTrue(child.winfo_viewable(), str(child))
        self.assertGreater(child.winfo_width(), 1)
        self.assertGreaterEqual(child.winfo_rootx(), parent.winfo_rootx(), str(child))
        self.assertGreaterEqual(child.winfo_rooty(), parent.winfo_rooty(), str(child))
        self.assertLessEqual(
            child.winfo_rootx() + child.winfo_width(),
            parent.winfo_rootx() + parent.winfo_width(),
            str(child),
        )
        self.assertLessEqual(
            child.winfo_rooty() + child.winfo_height(),
            parent.winfo_rooty() + parent.winfo_height(),
            str(child),
        )

    def assert_groups_inside(self, toolbar, parent) -> None:
        self.assert_inside(toolbar, parent)
        for group in toolbar.groups:
            self.assert_inside(group, toolbar)
            for child in group.winfo_children():
                if child.winfo_manager():
                    self.assert_inside(child, group)

    def test_scenario_rows_wrap_so_every_control_stays_visible(self) -> None:
        self.app.notebook.select(self.app.scenario_tab)
        # Two reports make the counter as long as it gets in practice.
        self.app.overview_run_ids = {self.first_id, self.second_id}
        self.app.overview_selection_explicit = True
        self.app._refresh_active_report_views()
        self.assertIn("цены только для 1 отчета", self.app.scenario_count_var.get())
        for width, height in ((1540, 920), (1180, 720)):
            for scale in (1.0, 0.9):
                with self.subTest(width=width, height=height, scale=scale):
                    self.app._apply_ui_scale(scale)
                    self.app.geometry(f"{width}x{height}+0+0")
                    self.settle()
                    tab = self.app.scenario_tab
                    self.assert_groups_inside(self.app.scenario_filters, tab)
                    self.assert_groups_inside(self.app.scenario_price_controls, tab)
                    self.assert_inside(self.app.scenario_reset_button, tab)
                    self.assert_inside(self.app.scenario_direction_combo, tab)
                    self.assert_inside(self.app.scenario_columns_button, tab)
                    self.assertIs(self.app.scenario_columns_button.master, self.app.scenario_filter_container)
                    filters_bottom = (
                        self.app.scenario_filter_container.winfo_rooty()
                        + self.app.scenario_filter_container.winfo_height()
                    )
                    self.assertGreaterEqual(self.app.scenario_tree.winfo_rooty(), filters_bottom)

    def test_report_list_shows_compact_labels_with_full_tooltip(self) -> None:
        self.settle()
        self.assertEqual(
            tuple(self.app.run_combo.cget("values")),
            ("№1 · Неделя 37 — проверено", "№2 · 15.09–19.09.2026"),
        )
        self.assertEqual(self.app.run_var.get(), "№2 · 15.09–19.09.2026")
        self.assertEqual(
            self.app._run_combo_tooltip_text(),
            "Отчет №2: Отчет Wildberries за 15.09.2026–19.09.2026\nПериод: 15.09.2026–19.09.2026",
        )
        self.app.run_var.set("№1 · Неделя 37 — проверено")
        self.app._on_run_selected()
        self.assertEqual(self.app.current_run_id, self.first_id)
        self.assertEqual(
            self.app._run_combo_tooltip_text(),
            "Отчет №1: Неделя 37 — проверено\nПериод: 08.09.2026–13.09.2026",
        )
        self.assertIn(
            "№1 · Неделя 37 — проверено · 08.09.2026–13.09.2026",
            tuple(self.app.compare_first_combo.cget("values")),
        )
        self.app.run_combo_tooltip.show(10, 10)
        self.settle()
        self.assertIsNotNone(self.app.run_combo_tooltip.tipwindow)
        self.app.run_combo_tooltip.hide()

    def test_every_overview_card_has_a_formula_tooltip(self) -> None:
        self.settle()
        cards = {
            **self.app.kpi_cards,
            **{f"share:{key}": card for key, card in self.app.revenue_share_kpi_cards.items()},
            **{f"category:{key}": card for key, card in self.app.category_kpi_cards.items()},
        }
        self.assertEqual(len(cards), 17)
        self.assertEqual(sorted(self.app.overview_card_tooltips), sorted(cards))
        help_text = help_plain_text(OVERVIEW_HELP_CONTENT)
        for key, tooltip in self.app.overview_card_tooltips.items():
            with self.subTest(card=key):
                self.assertIs(tooltip.widget, cards[key])
                self.assertIn(tooltip.text().splitlines()[0], help_text)
        self.assertIn(
            "Налог с нераспределённых операций не начисляется",
            self.app.overview_card_tooltips["report_total"].text(),
        )
        self.assertIn(
            "уже учтена в сумме «К перечислению продавцу»",
            self.app.overview_card_tooltips["share:commission"].text(),
        )
        tooltip = self.app.overview_card_tooltips["share:points"]
        tooltip.show(10, 10)
        self.settle()
        self.assertIsNotNone(tooltip.tipwindow)
        tooltip.hide()
        self.assertIsNone(tooltip.tipwindow)

    def test_loyalty_card_title(self) -> None:
        self.settle()
        titles = [
            str(child.cget("text"))
            for child in self.app.revenue_share_kpi_cards["points"].winfo_children()
            if child.winfo_class() == "TLabel" and str(child.cget("text"))
        ]
        # The first label is the title; the second one shows the value.
        self.assertEqual(titles[0], POINTS_CARD_TITLE)
        self.assertNotIn("Баллы", titles)


if __name__ == "__main__":
    unittest.main()
