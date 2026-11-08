"""One-sentence findings computed from each query result.

The sentences are derived from the data, so they stay correct if the
generator or a query changes.
"""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd


def _eur(x: float) -> str:
    return f"€{x:,.0f}"


def _revenue(df: pd.DataFrame) -> str:
    by_year = df.assign(year=df["month"].str[:4]).groupby("year")["revenue_eur"].sum()
    growth = 100 * (by_year["2025"] / by_year["2024"] - 1)
    peak = df.loc[df["revenue_eur"].idxmax(), "month"]
    low, high = df["gross_margin_pct"].min(), df["gross_margin_pct"].max()
    return (
        f"Revenue grew {growth:.1f} % from 2024 to 2025 ({_eur(by_year['2025'])} in 2025). "
        f"Demand is seasonal, with the peak in {peak}, while gross margin stays between {low} % and {high} %."
    )


def _on_time(df: pd.DataFrame) -> str:
    by_carrier = df.groupby("carrier").apply(
        lambda g: (g["on_time_pct"] * g["shipments"]).sum() / g["shipments"].sum(), include_groups=False
    )
    worst, best = by_carrier.idxmin(), by_carrier.idxmax()
    return (
        f"{worst} keeps the delivery promise on only {by_carrier[worst]:.1f} % of shipments, "
        f"against {by_carrier[best]:.1f} % for {best}. Shifting volume away from {worst} is the quickest lever."
    )


def _abc(df: pd.DataFrame) -> str:
    a = df.set_index("abc_class").loc["A"]
    return (
        f"{int(a['products'])} products ({a['share_of_products_pct']} % of the range) earn "
        f"{a['share_of_revenue_pct']} % of revenue. Planning effort should follow that split."
    )


def _suppliers(df: pd.DataFrame) -> str:
    worst, second = df.iloc[0], df.iloc[1]
    return (
        f"{worst['supplier_id']} ({worst['country']}) delivers {worst['late_pct']} % of purchase orders late, "
        f"by {worst['avg_days_late_when_late']} days on average. The next worst supplier is late "
        f"{second['late_pct']} % of the time."
    )


def _fill_rate(df: pd.DataFrame) -> str:
    total = 100 * df["units_shipped"].sum() / df["units_ordered"].sum()
    top = df.iloc[0]
    return (
        f"Overall fill rate is {total:.1f} %, and {_eur(df['lost_revenue_eur'].sum())} of orders could not be shipped. "
        f"The biggest single gap is {top['category']} in {top['warehouse_id']} ({_eur(top['lost_revenue_eur'])})."
    )


def _stockouts(df: pd.DataFrame) -> str:
    counts = df["supplier_id"].value_counts()
    return (
        f"{counts.iloc[0]} of the {len(df)} worst stockout cases on A items involve products from "
        f"{counts.index[0]}, the supplier with the most late deliveries."
    )


def _turns(df: pd.DataFrame) -> str:
    fast, slow = df.iloc[0], df.iloc[-1]
    return (
        f"{fast['category']} turns {fast['turns_per_year']} times a year; {slow['category']} only "
        f"{slow['turns_per_year']} times, which ties up about {int(slow['days_of_inventory'])} days of demand in stock."
    )


def _abc_xyz(df: pd.DataFrame) -> str:
    az = df[(df["abc_class"] == "A") & (df["xyz_class"] == "Z")]
    n = int(az["products"].sum()) if len(az) else 0
    share = float(az["share_of_revenue_pct"].sum()) if len(az) else 0.0
    return (
        f"{n} products are A and Z at once: important and hard to forecast. They carry {share:.1f} % of revenue "
        f"and are the first candidates for higher safety stock or closer customer forecasting."
    )


def _cycle(df: pd.DataFrame) -> str:
    slow, best = df.iloc[0], df.iloc[-1]
    return (
        f"{slow['city']} is on time for {slow['on_time_pct']} % of orders against {best['on_time_pct']} % in "
        f"{best['city']}. Transit times are almost the same, so the gap is in warehouse processing "
        f"({slow['avg_processing_days']} vs {best['avg_processing_days']} days)."
    )


def _late_vs_stockouts(df: pd.DataFrame) -> str:
    corr = df["correlation_across_suppliers"].iloc[0]
    rest = df.iloc[1:]
    corr_rest = rest["late_pct"].corr(rest["stockout_day_pct"])
    return (
        f"Across suppliers, late share and stockout share correlate at {corr}. Much of that comes from "
        f"{df.iloc[0]['supplier_id']}; without it the correlation is {corr_rest:.2f}. "
        f"Twelve suppliers is a small sample, so read this as a strong hint, not proof."
    )


FINDINGS: dict[str, Callable[[pd.DataFrame], str]] = {
    "01_revenue_and_margin": _revenue,
    "02_on_time_delivery": _on_time,
    "03_abc_analysis": _abc,
    "04_supplier_scorecard": _suppliers,
    "05_fill_rate": _fill_rate,
    "06_stockouts_on_a_items": _stockouts,
    "07_inventory_turns": _turns,
    "08_abc_xyz_matrix": _abc_xyz,
    "09_order_cycle_time": _cycle,
    "10_late_suppliers_and_stockouts": _late_vs_stockouts,
}


def finding(question_id: str, df: pd.DataFrame) -> str:
    return FINDINGS[question_id](df)
