from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Iterable

from .ui import (
    CATEGORY_ALL,
    CATEGORY_EMPTY,
    SORT_ASCENDING,
    SORT_NONE,
    _category_label,
    _money,
    _number,
    _profitability_text,
    _russian_position_word,
    summarize_category,
)
from .ui_layout import DisplayWBPriceAnalyzerApp


def category_filter_label(selected: set[str] | frozenset[str]) -> str:
    """Text of the category button; an empty selection means all categories."""
    values = sorted(selected, key=str.casefold)
    if not values:
        return CATEGORY_ALL
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return " · ".join(values)
    return f"Выбрано категорий: {len(values)}"


def category_filter_scope_text(
    selected: set[str] | frozenset[str],
    *,
    exclude: bool = False,
) -> str:
    values = sorted(selected, key=str.casefold)
    if not values:
        return "Все товары"
    names = ", ".join(values[:3])
    if len(values) > 3:
        names += f" и ещё {len(values) - 3}"
    return f"кроме категорий: {names}" if exclude else f"категории: {names}"


def category_allowed(category: str, selected: set[str] | frozenset[str], exclude: bool) -> bool:
    """Empty selection keeps every row in both include and exclude modes."""
    if not selected:
        return True
    contains = category in selected
    return not contains if exclude else contains


class CategorySelectionDialog(tk.Toplevel):
    def __init__(
        self,
        owner: tk.Misc,
        categories: list[str],
        selected: set[str],
        *,
        title: str = "Фильтр категорий",
    ) -> None:
        super().__init__(owner)
        self.title(title)
        self.geometry("540x540")
        self.minsize(440, 420)
        self.transient(owner.winfo_toplevel())
        self.categories = categories
        self.result: set[str] | None = None
        self.cancelled = True
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        ttk.Label(self, text="Выберите одну или несколько категорий", style="Section.TLabel").grid(
            row=0, column=0, sticky="w", padx=20, pady=(18, 3)
        )
        ttk.Label(
            self,
            text=(
                "Обычный щелчок включает или выключает категорию. "
                "Пустой выбор означает «Все категории»."
            ),
            style="Muted.TLabel",
            wraplength=500,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 10))

        box = ttk.Frame(self)
        box.grid(row=2, column=0, sticky="nsew", padx=20)
        box.columnconfigure(0, weight=1)
        box.rowconfigure(0, weight=1)
        self.listbox = tk.Listbox(
            box,
            selectmode=tk.MULTIPLE,
            exportselection=False,
            activestyle="dotbox",
            borderwidth=1,
            highlightthickness=0,
        )
        scroll = ttk.Scrollbar(box, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scroll.set)
        self.listbox.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        for index, item in enumerate(categories):
            self.listbox.insert("end", item)
            if item in selected:
                self.listbox.selection_set(index)

        controls = ttk.Frame(self)
        controls.grid(row=3, column=0, sticky="ew", padx=20, pady=(10, 0))
        controls.columnconfigure(2, weight=1)
        ttk.Button(controls, text="Выбрать все", command=self._select_all).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(controls, text="Снять все", command=self._clear).grid(row=0, column=1, padx=(0, 6))
        self.summary_var = tk.StringVar()
        ttk.Label(controls, textvariable=self.summary_var, style="Muted.TLabel").grid(
            row=0, column=2, sticky="e"
        )

        footer = ttk.Frame(self, padding=(20, 14, 20, 18))
        footer.grid(row=4, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        ttk.Button(footer, text="Отмена", command=self._cancel).grid(row=0, column=1, padx=4)
        ttk.Button(footer, text="Применить", style="Accent.TButton", command=self._apply).grid(
            row=0, column=2, padx=4
        )

        self.listbox.bind("<<ListboxSelect>>", lambda _event: self._update_summary())
        self.bind("<Escape>", lambda _event: self._cancel())
        self.bind("<Return>", lambda _event: self._apply())
        self._update_summary()
        self.after_idle(self._open)

    def _open(self) -> None:
        try:
            self.grab_set()
            self.lift()
            self.focus_force()
        except tk.TclError:
            pass

    def _select_all(self) -> None:
        if self.categories:
            self.listbox.selection_set(0, "end")
        self._update_summary()

    def _clear(self) -> None:
        self.listbox.selection_clear(0, "end")
        self._update_summary()

    def _update_summary(self) -> None:
        count = len(self.listbox.curselection())
        self.summary_var.set(CATEGORY_ALL if count == 0 else f"Выбрано: {count}")

    def _apply(self) -> None:
        self.result = {self.categories[int(index)] for index in self.listbox.curselection()}
        self.cancelled = False
        self.destroy()

    def _cancel(self) -> None:
        self.cancelled = True
        self.destroy()


class CategoryWBPriceAnalyzerApp(DisplayWBPriceAnalyzerApp):
    def __init__(self, *args, **kwargs) -> None:
        self._category_selected: dict[str, set[str]] = {"overview": set(), "scenario": set()}
        self._category_label_vars: dict[str, tk.StringVar] = {}
        self._category_exclude_vars: dict[str, tk.BooleanVar] = {}
        super().__init__(*args, **kwargs)

    def _build_ui(self) -> None:
        super()._build_ui()
        self._install_category_filters()

    def _install_category_filters(self) -> None:
        self._category_label_vars = {
            "overview": tk.StringVar(value=CATEGORY_ALL),
            "scenario": tk.StringVar(value=CATEGORY_ALL),
        }
        self._category_exclude_vars = {
            "overview": tk.BooleanVar(value=False),
            "scenario": tk.BooleanVar(value=False),
        }
        self._replace("overview", self.overview_category_combo, self.overview_category_var)
        self._replace("scenario", self.scenario_category_combo, self.scenario_category_var)

    def _replace(self, key: str, combo: ttk.Combobox, legacy_var: tk.StringVar) -> None:
        parent = combo.master
        try:
            info = combo.grid_info()
            row = int(info.get("row", 0))
            col = int(info.get("column", 1))
        except (tk.TclError, TypeError, ValueError):
            return
        for child in parent.winfo_children():
            if child is combo or child.winfo_manager() != "grid":
                continue
            try:
                child_column = int(child.grid_info().get("column", 0))
                if child_column >= col + 1:
                    child.grid_configure(column=child_column + 1)
            except (tk.TclError, TypeError, ValueError):
                pass
        combo.grid_remove()
        legacy_var.set(CATEGORY_ALL)
        style = "Compact.TButton" if key == "overview" else "TButton"
        ttk.Button(
            parent,
            textvariable=self._category_label_vars[key],
            command=lambda: self._choose_categories(key),
            width=24,
            style=style,
        ).grid(row=row, column=col, padx=(0, 8))
        ttk.Checkbutton(
            parent,
            text="Исключить выбранные",
            variable=self._category_exclude_vars[key],
            command=lambda: self._on_category_mode_changed(key),
        ).grid(row=row, column=col + 1, sticky="w", padx=(0, 12))

    def _category_source(self, key: str):
        if key == "overview":
            return self.overview_calculation
        return self._active_report_calculation()

    def _available_categories(self, key: str) -> list[str]:
        calculation = self._category_source(key)
        products = calculation.products if calculation is not None else []
        return sorted({_category_label(row.category) for row in products}, key=str.casefold)

    def _normalize_category_selection(self, key: str) -> None:
        self._category_selected[key].intersection_update(self._available_categories(key))
        self._category_label_vars[key].set(category_filter_label(self._category_selected[key]))

    def _choose_categories(self, key: str) -> None:
        categories = self._available_categories(key)
        if not categories:
            messagebox.showinfo(
                "Фильтр категорий",
                "В текущем отчете нет категорий для выбора.",
                parent=self,
            )
            return
        dialog = CategorySelectionDialog(
            self,
            categories,
            self._category_selected[key],
            title="Категории — Обзор" if key == "overview" else "Категории — Сценарий цены",
        )
        self.wait_window(dialog)
        if dialog.cancelled or dialog.result is None:
            return
        self._category_selected[key] = dialog.result
        self._category_label_vars[key].set(category_filter_label(dialog.result))
        self._refresh_category_view(key)

    def _on_category_mode_changed(self, key: str) -> None:
        self._refresh_category_view(key)

    def _refresh_category_view(self, key: str) -> None:
        if key == "overview":
            self._populate_overview()
        else:
            self._populate_scenario()

    def _category_matches(self, key: str, category: str) -> bool:
        return category_allowed(
            category,
            self._category_selected[key],
            bool(self._category_exclude_vars[key].get()),
        )

    def _remove_filtered_rows(self, key: str, tree: ttk.Treeview) -> None:
        for iid in tuple(tree.get_children("")):
            values = tree.item(iid, "values")
            category = str(values[2]) if len(values) > 2 else CATEGORY_EMPTY
            if not self._category_matches(key, category):
                tree.delete(iid)

    def _filtered_products(self, key: str, products: Iterable) -> list:
        return [row for row in products if self._category_matches(key, _category_label(row.category))]

    def _populate_overview(self) -> None:
        if not self._category_label_vars:
            super()._populate_overview()
            return
        self.overview_category_var.set(CATEGORY_ALL)
        super()._populate_overview()
        calculation = self.overview_calculation
        if calculation is None:
            return
        self._normalize_category_selection("overview")
        self._remove_filtered_rows("overview", self.overview_tree)
        rows = self._filtered_products("overview", calculation.products)
        totals = summarize_category(rows, calculation.tax_rate, CATEGORY_ALL)
        count = int(totals["product_count"])
        scope = category_filter_scope_text(
            self._category_selected["overview"],
            exclude=bool(self._category_exclude_vars["overview"].get()),
        )
        self.category_summary_title_var.set(
            f"Итоги по фильтру: {scope} · {count} {_russian_position_word(count)}"
        )
        self.category_kpi_vars["revenue"].set(_money(totals["revenue"]))
        self.category_kpi_vars["net_profit"].set(_money(totals["net_profit"]))
        self.category_kpi_vars["profitability"].set(
            _profitability_text(
                totals["profitability"] if totals["cost_sold"] else None,
                units=totals["units"],
                cost_sold=totals["cost_sold"],
            )
        )
        self.category_kpi_vars["units"].set(_number(totals["units"]))
        self.category_kpi_vars["cost_sold"].set(_money(totals["cost_sold"]))
        self.category_kpi_vars["financial_result"].set(_money(totals["financial_result"]))
        self.overview_count_var.set(
            f"Показано: {len(self.overview_tree.get_children(''))} из {len(calculation.products)}"
        )

    def _populate_scenario(self) -> None:
        if not self._category_label_vars:
            super()._populate_scenario()
            return
        self.scenario_category_var.set(CATEGORY_ALL)
        super()._populate_scenario()
        # The table shows the active report set, so the cards and category list
        # must use the same calculation, not only the report open in the top list.
        calculation = self._active_report_calculation()
        if calculation is None:
            return
        self._normalize_category_selection("scenario")
        self._remove_filtered_rows("scenario", self.scenario_tree)
        results = self._filtered_products("scenario", calculation.products)
        scenarios = [self.scenario_rows[row.article] for row in results if row.article in self.scenario_rows]
        priced = [row for row in scenarios if row.net_profit_per_unit is not None]
        current = sum(row.revenue_including_points for row in results)
        planned = sum(float(row.planned_revenue or 0) for row in scenarios)
        net = sum(float(row.net_profit_per_unit) * row.units for row in priced)
        cost = sum(row.unit_cost * row.units for row in priced)
        units = sum(row.units for row in scenarios)
        self.scenario_kpi_vars["current_revenue"].set(_money(current))
        self.scenario_kpi_vars["planned_revenue"].set(_money(planned))
        self.scenario_kpi_vars["planned_net"].set(_money(net))
        self.scenario_kpi_vars["planned_margin"].set(
            _profitability_text(net / cost if cost else None, units=units, cost_sold=cost)
        )
        self.scenario_count_var.set(
            f"Показано: {len(self.scenario_tree.get_children(''))} из {len(self.scenario_rows)}"
            f"{self._scenario_scope_note()}"
        )

    def _reset_overview_filters(self) -> None:
        self._category_selected["overview"] = set()
        if self._category_label_vars:
            self._category_label_vars["overview"].set(CATEGORY_ALL)
            self._category_exclude_vars["overview"].set(False)
        self.overview_category_var.set(CATEGORY_ALL)
        self.overview_article_var.set("")
        self.overview_sort_var.set(SORT_NONE)
        self.overview_sort_direction_var.set(SORT_ASCENDING)
        self._populate_overview()

    def _reset_scenario_filters(self) -> None:
        self._category_selected["scenario"] = set()
        if self._category_label_vars:
            self._category_label_vars["scenario"].set(CATEGORY_ALL)
            self._category_exclude_vars["scenario"].set(False)
        self.scenario_category_var.set(CATEGORY_ALL)
        self.scenario_article_var.set("")
        self.scenario_sort_var.set(SORT_NONE)
        self.scenario_sort_direction_var.set(SORT_ASCENDING)
        self._populate_scenario()
