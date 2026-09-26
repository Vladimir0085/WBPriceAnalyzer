from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .column_settings import ColumnSettingsWBPriceAnalyzerApp
from .help_content import (
    CATEGORY_CARD_HELP,
    OVERVIEW_CARD_HELP,
    REVENUE_SHARE_CARD_HELP,
    card_tooltip_text,
)
from .ui import _money, _percent, _profitability_text
from .widget_tooltips import HoverTooltip


# In WB the loyalty programme fee and withheld points are an expense.
POINTS_CARD_TITLE = "Лояльность и баллы (расход)"


def report_total_value(calculation) -> float:
    """Чистая прибыль от деятельности: чистая прибыль товаров + нераспределённые."""
    return float(calculation.totals()["net_profit"])


def report_total_profitability(calculation) -> float:
    """Чистая прибыль от деятельности, делённая на себестоимость проданного."""
    cost_sold = float(calculation.totals()["cost_sold"])
    return report_total_value(calculation) / cost_sold if cost_sold else 0.0


def overview_revenue_kpi_values(calculation) -> dict[str, str]:
    """Format paired monetary and relative KPIs for the Overview tab."""
    amounts = calculation.revenue_amounts()
    shares = calculation.revenue_shares()
    return {
        "commission": f"{_money(amounts['commission'])} · {_percent(shares['commission_share'])}",
        "logistics": f"{_money(amounts['logistics'])} · {_percent(shares['logistics_share'])}",
        "points": f"{_money(amounts['points'])} · {_percent(shares['points_share'])}",
        "net_margin": _percent(shares["net_margin"]),
    }


class ReportTotalsWBPriceAnalyzerApp(ColumnSettingsWBPriceAnalyzerApp):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._install_report_total_kpi()
        self._install_revenue_share_kpis()
        self._install_overview_card_tooltips()
        self._refresh_report_kpis()

    def _install_report_total_kpi(self) -> None:
        self.kpi_frame.columnconfigure(6, weight=1)
        for child in self.kpi_frame.winfo_children():
            try:
                row = int(child.grid_info().get("row", -1))
            except (TypeError, ValueError, tk.TclError):
                continue
            if row in (0, 2):
                child.grid_configure(columnspan=7)

        self.kpi_vars["report_total"] = tk.StringVar(master=self, value="—")
        self.kpi_vars["report_total_profitability"] = tk.StringVar(
            master=self,
            value="—",
        )
        card = ttk.Frame(self.kpi_frame, style="Card.TFrame", padding=(8, 5))
        card.grid(row=1, column=6, sticky="nsew", padx=(5, 0))
        if hasattr(self, "kpi_cards"):
            self.kpi_cards["report_total"] = card
        ttk.Label(
            card,
            text="Чистая прибыль от деятельности",
            style="CompactCardMuted.TLabel",
        ).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(
            card,
            textvariable=self.kpi_vars["report_total"],
            style="CompactKpi.TLabel",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(1, 0))
        ttk.Label(
            card,
            text="Доходность:",
            style="CompactCardMuted.TLabel",
        ).grid(row=2, column=0, sticky="w", pady=(2, 0))
        ttk.Label(
            card,
            textvariable=self.kpi_vars["report_total_profitability"],
            style="CompactCard.TLabel",
        ).grid(row=2, column=1, sticky="w", padx=(5, 0), pady=(2, 0))

    def _install_revenue_share_kpis(self) -> None:
        for child in self.kpi_frame.winfo_children():
            try:
                row = int(child.grid_info().get("row", -1))
            except (TypeError, ValueError, tk.TclError):
                continue
            if row == 2:
                child.grid_configure(row=3, columnspan=7)
            elif row == 3:
                child.grid_configure(row=4)

        share_frame = ttk.Frame(self.kpi_frame)
        share_frame.grid(row=2, column=0, columnspan=7, sticky="ew", pady=(3, 2))
        for column in range(4):
            share_frame.columnconfigure(column, weight=1)

        self.revenue_share_kpi_vars: dict[str, tk.StringVar] = {}
        self.revenue_share_kpi_cards: dict[str, ttk.Frame] = {}
        cards = (
            ("commission", "Комиссия WB"),
            ("logistics", "Логистика"),
            ("points", POINTS_CARD_TITLE),
            ("net_margin", "Чистая прибыль, %"),
        )
        for index, (key, title) in enumerate(cards):
            variable = tk.StringVar(master=self, value="—")
            self.revenue_share_kpi_vars[key] = variable
            card = ttk.Frame(share_frame, style="Card.TFrame", padding=(8, 5))
            card.columnconfigure(1, weight=1)
            self.revenue_share_kpi_cards[key] = card
            card.grid(
                row=0,
                column=index,
                sticky="nsew",
                padx=(0 if index == 0 else 5, 0 if index == len(cards) - 1 else 5),
            )
            ttk.Label(card, text=title, style="CompactCardMuted.TLabel").grid(
                row=0, column=0, sticky="w"
            )
            ttk.Label(card, textvariable=variable, style="CompactKpi.TLabel").grid(
                row=0, column=1, sticky="e", padx=(8, 0)
            )

    def _install_overview_card_tooltips(self) -> None:
        """Show the formula from «Справка» when hovering over any Overview card."""
        self.overview_card_tooltips: dict[str, HoverTooltip] = {}
        groups = (
            ("", getattr(self, "kpi_cards", {}), OVERVIEW_CARD_HELP),
            ("share:", getattr(self, "revenue_share_kpi_cards", {}), REVENUE_SHARE_CARD_HELP),
            ("category:", getattr(self, "category_kpi_cards", {}), CATEGORY_CARD_HELP),
        )
        for prefix, cards, card_help in groups:
            for key, card in cards.items():
                if key in card_help:
                    self.overview_card_tooltips[prefix + key] = HoverTooltip(
                        card, card_tooltip_text(card_help[key])
                    )

    def _populate_overview(self) -> None:
        super()._populate_overview()
        self._refresh_report_kpis()

    def _clear_current_view(self) -> None:
        super()._clear_current_view()
        self._refresh_report_kpis()

    def _refresh_report_kpis(self) -> None:
        calculation = self.overview_calculation
        report_total = self.kpi_vars.get("report_total")
        report_total_profitability_var = self.kpi_vars.get(
            "report_total_profitability"
        )
        share_variables = getattr(self, "revenue_share_kpi_vars", None)
        if calculation is None:
            if report_total is not None:
                report_total.set("—")
            if report_total_profitability_var is not None:
                report_total_profitability_var.set("—")
            if share_variables:
                for variable in share_variables.values():
                    variable.set("—")
            return

        product_net = sum(
            item.net_profit(calculation.tax_rate)
            for item in calculation.products
        )
        cost_sold = sum(item.cost_sold for item in calculation.products)
        units = sum(item.units for item in calculation.products)
        self.kpi_vars["net_profit"].set(_money(product_net))
        self.kpi_vars["profitability"].set(
            _profitability_text(
                product_net / cost_sold if cost_sold else None,
                units=units,
                cost_sold=cost_sold,
            )
        )
        if report_total is not None:
            report_total.set(_money(report_total_value(calculation)))
        if report_total_profitability_var is not None:
            report_total_profitability_var.set(
                _profitability_text(
                    report_total_profitability(calculation)
                    if cost_sold
                    else None,
                    units=units,
                    cost_sold=cost_sold,
                )
            )
        if share_variables:
            values = overview_revenue_kpi_values(calculation)
            for key, variable in share_variables.items():
                variable.set(values[key])


def run_app() -> None:
    from .single_instance import launch_single_instance

    launch_single_instance(ReportTotalsWBPriceAnalyzerApp)
