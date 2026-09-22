from __future__ import annotations

import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from wb_app.service import AppService
from wb_app.ui_containers import ScrollableSummary, summary_scrollbars, wrapped_positions
from wb_app.ui_layout import DisplayWBPriceAnalyzerApp, StaticTableLayout, TableModeController


class FilterWrappingTests(unittest.TestCase):
    def test_controls_fit_on_one_row_on_a_wide_monitor(self) -> None:
        positions, height = wrapped_positions([(450, 36), (250, 30), (300, 32)], 1100)
        self.assertEqual(positions, [(0, 0), (458, 0), (716, 0)])
        self.assertEqual(height, 36)

    def test_controls_wrap_without_clipping_at_common_widths_and_dpi(self) -> None:
        for width in (880, 1140, 1280, 1500, 1860):
            for scale in (1.0, 1.25, 1.5, 2.0):
                with self.subTest(width=width, scale=scale):
                    sizes = [(round(w * scale), round(h * scale)) for w, h in
                             ((410, 36), (200, 32), (250, 32), (200, 32), (95, 36), (130, 24))]
                    positions, height = wrapped_positions(sizes, width)
                    for index, ((x, y), (w, h)) in enumerate(zip(positions, sizes)):
                        self.assertLessEqual(x + w, width)
                        self.assertLessEqual(y + h, height)
                        for (previous_x, previous_y), (previous_w, previous_h) in zip(
                            positions[:index], sizes[:index]
                        ):
                            self.assertTrue(
                                x >= previous_x + previous_w or y >= previous_y + previous_h
                            )

    def test_next_row_uses_the_tallest_control_in_the_previous_row(self) -> None:
        positions, height = wrapped_positions([(300, 30), (200, 48), (350, 32)], 600)
        self.assertEqual(positions, [(0, 0), (308, 0), (0, 52)])
        self.assertEqual(height, 84)

    def test_resize_back_to_a_wide_window_removes_extra_rows(self) -> None:
        sizes = [(400, 36), (250, 32), (250, 32)]
        self.assertGreater(wrapped_positions(sizes, 700)[1], 36)
        self.assertEqual(wrapped_positions(sizes, 1200)[1], 36)
        self.assertEqual(wrapped_positions([], 1), ([], 0))

    def test_one_control_is_placed_even_before_the_window_is_mapped(self) -> None:
        self.assertEqual(wrapped_positions([(100, 32)], 0), ([(0, 0)], 32))


class SummaryViewportTests(unittest.TestCase):
    def test_no_scrollbars_when_summary_fits(self) -> None:
        self.assertEqual(summary_scrollbars(1200, 360, 1100, 320, 15, 15), (False, False))

    def test_short_window_scrolls_summary_instead_of_covering_filters(self) -> None:
        self.assertEqual(summary_scrollbars(1200, 200, 1100, 320, 15, 15), (False, True))

    def test_scrollbars_account_for_space_taken_by_each_other(self) -> None:
        self.assertEqual(summary_scrollbars(1200, 320, 1190, 330, 15, 15), (True, True))
        self.assertEqual(summary_scrollbars(1200, 320, 1250, 310, 15, 15), (True, True))


class PinnedControlsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.upper = Mock()
        self.upper.winfo_manager.return_value = "grid"
        self.layout = StaticTableLayout(Mock(), Mock(), self.upper, Mock(), Mock(), 210, 0.5)
        self.owner = Mock()
        self.owner._protect_layout = lambda layout: DisplayWBPriceAnalyzerApp._protect_layout(
            self.owner, layout
        )
        with patch("wb_app.ui_layout.ttk.Button"):
            self.controller = TableModeController(
                self.owner, "overview", "Обзор", self.layout.tab, Mock(), self.layout
            )

    def test_filters_are_outside_the_summary_and_table_split(self) -> None:
        app = SimpleNamespace(
            overview_tab=self.layout.tab, _table_layouts={self.layout.tab: self.layout}
        )
        with patch("wb_app.ui_layout.WrappingToolbar") as bar:
            result = DisplayWBPriceAnalyzerApp._create_overview_filters(app, self.layout.table)
        bar.assert_called_once_with(self.layout.toolbar)
        self.assertIs(result, bar.return_value)
        result.grid.assert_called_once_with(
            row=0, column=0, columnspan=3, sticky="ew", pady=(2, 4)
        )

    def test_fullscreen_keeps_filters_and_buttons_in_a_separate_row(self) -> None:
        self.controller.expand()
        self.assertTrue(self.controller.fullscreen)
        self.upper.grid_remove.assert_called_once()
        self.layout.toolbar.grid_remove.assert_not_called()
        self.layout.table.grid_configure.assert_not_called()
        self.layout.shell.rowconfigure.assert_any_call(0, weight=0, minsize=0, uniform="")
        self.layout.shell.rowconfigure.assert_any_call(2, weight=1, minsize=110, uniform="")
        self.controller.fullscreen_button.configure.assert_called_with(text="Вернуть обычный вид")

    def test_restore_preserves_the_equal_split(self) -> None:
        self.controller.expand()
        self.controller.restore()
        self.assertFalse(self.controller.fullscreen)
        self.upper.grid.assert_called_once()
        group = f"split_{id(self.layout.shell)}"
        self.layout.shell.rowconfigure.assert_any_call(0, minsize=0, weight=50, uniform=group)
        self.layout.shell.rowconfigure.assert_any_call(2, minsize=110, weight=50, uniform=group)

    def test_scaling_does_not_reintroduce_empty_summary_space_in_fullscreen(self) -> None:
        self.controller.expand()
        self.upper.winfo_manager.return_value = ""
        self.layout.shell.reset_mock()
        self.owner._protect_layout(self.layout)
        self.layout.shell.rowconfigure.assert_not_called()


class OverviewTkGeometryTests(unittest.TestCase):
    """Run against real widgets on Windows or with a display (e.g. xvfb-run)."""

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
        from wb_app.report_totals import ReportTotalsWBPriceAnalyzerApp

        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.callback_errors = []
        callback_patch = patch(
            "tkinter.Tk.report_callback_exception",
            side_effect=lambda *error: self.callback_errors.append(error),
        )
        callback_patch.start()
        self.addCleanup(callback_patch.stop)
        self.app = ReportTotalsWBPriceAnalyzerApp(
            AppService(Path(self.directory.name))
        )
        self.addCleanup(self.app.destroy)
        self.app.minsize(1, 1)
        # Test fixed DPI values rather than multiplying the runner's own DPI.
        self.app._base_tk_scaling = 96 / 72

    def settle(self) -> None:
        for _ in range(3):
            self.app.update_idletasks()
            self.app.update()
        self.assertEqual(self.callback_errors, [])

    def assert_visible_in(self, child, parent) -> None:
        self.assertTrue(child.winfo_viewable(), str(child))
        self.assertGreater(child.winfo_width(), 1)
        self.assertGreater(child.winfo_height(), 1)
        self.assertGreaterEqual(child.winfo_rootx(), parent.winfo_rootx())
        self.assertGreaterEqual(child.winfo_rooty(), parent.winfo_rooty())
        self.assertLessEqual(
            child.winfo_rootx() + child.winfo_width(),
            parent.winfo_rootx() + parent.winfo_width(),
        )
        self.assertLessEqual(
            child.winfo_rooty() + child.winfo_height(),
            parent.winfo_rooty() + parent.winfo_height(),
        )

    def assert_filters_visible(self) -> None:
        filters = self.app.overview_filters
        self.assert_visible_in(filters, self.app.overview_tab)
        self.assert_visible_in(filters, filters.master)
        for group in filters.groups:
            self.assert_visible_in(group, filters)
            for child in group.winfo_children():
                if child.winfo_manager():
                    self.assert_visible_in(child, group)
        self.assertGreaterEqual(
            self.app.overview_tree.winfo_rooty(), filters.winfo_rooty() + filters.winfo_height()
        )

    def test_filters_visible_on_laptop_and_desktop_with_dpi_scaling(self) -> None:
        for scale in (1.0, 1.5, 2.0):
            self.app._apply_ui_scale(scale)
            for width, height in ((1180, 608), (1318, 688), (1540, 920), (1860, 960)):
                with self.subTest(scale=scale, width=width, height=height):
                    self.app.geometry(f"{width}x{height}+0+0")
                    self.settle()
                    self.assert_filters_visible()
                    layout = self.app._table_layouts[self.app.overview_tab]
                    self.assertLessEqual(abs(layout.table.winfo_height() - layout.upper.winfo_height()), 2)
                    self.assert_visible_in(self.app.overview_tree, layout.table)

    def test_filters_survive_fullscreen_scale_and_restore(self) -> None:
        self.app.geometry("1318x688+0+0")
        self.settle()
        controller = self.app._table_modes["overview"]
        normal_height = self.app.overview_tree.winfo_height()
        controller.expand()
        self.app._apply_ui_scale(1.25)
        self.settle()
        self.assert_filters_visible()
        self.assertGreater(self.app.overview_tree.winfo_height(), normal_height)
        controller.restore()
        self.settle()
        self.assert_filters_visible()

    def test_small_window_summary_is_scrollable_independently_of_filters(self) -> None:
        # Force overflow even with the smaller default fonts on Windows CI.
        # A 608px-high window can fit the compact summary without scrolling.
        self.app.geometry("1180x420+0+0")
        self.settle()
        summary = self.app._table_layouts[self.app.overview_tab].upper
        self.assertIsInstance(summary, ScrollableSummary)
        self.assertGreater(summary.content.winfo_reqheight(), summary.canvas.winfo_height())
        self.assertTrue(summary.yscroll.winfo_viewable())
        filters_y = self.app.overview_filters.winfo_rooty()
        summary.canvas.yview_moveto(1)
        self.settle()
        self.assertGreater(summary.canvas.yview()[0], 0)
        self.assertEqual(self.app.overview_filters.winfo_rooty(), filters_y)
        self.assert_filters_visible()


if __name__ == "__main__":
    unittest.main()
