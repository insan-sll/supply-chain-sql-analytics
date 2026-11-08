"""Streamlit front end: ten supply-chain questions answered in SQL."""

from __future__ import annotations

import tempfile
from pathlib import Path

import altair as alt
import duckdb
import pandas as pd
import streamlit as st

from scsql.db import build_file
from scsql.findings import finding
from scsql.playground import MAX_ROWS, QueryRejected, prepare
from scsql.questions import load_questions

st.set_page_config(page_title="Supply Chain SQL Analytics", page_icon="📦", layout="wide")

ACCENT = "#f5a524"
TABLES = {
    "suppliers": "12 suppliers with country and promised lead time",
    "warehouses": "3 warehouses (Augsburg, Hamburg, Leipzig)",
    "products": "200 SKUs in 5 categories with cost, price and supplier",
    "orders": "Customer orders with date, region and serving warehouse",
    "order_lines": "Ordered and shipped quantity per product and order",
    "shipments": "Outbound shipments with carrier, promised and delivered date",
    "purchase_orders": "Replenishment orders with expected and received date",
    "inventory_daily": "End-of-day stock per product and warehouse",
}


@st.cache_resource(show_spinner="Generating two years of data and building the database…")
def database() -> Path:
    return build_file(Path(tempfile.gettempdir()) / "scsql.duckdb")


def run(sql: str) -> pd.DataFrame:
    con = duckdb.connect(str(database()), read_only=True, config={"enable_external_access": False})
    try:
        return con.execute(sql).df()
    finally:
        con.close()


@st.cache_data(show_spinner=False)
def run_cached(sql: str) -> pd.DataFrame:
    return run(sql)


def bar(df, x, y, color=None, sort="-y", horizontal=False):
    enc = {
        "x": alt.X(f"{y}:Q") if horizontal else alt.X(f"{x}:N", sort=sort, title=None),
        "y": alt.Y(f"{x}:N", sort="-x", title=None) if horizontal else alt.Y(f"{y}:Q"),
        "tooltip": list(df.columns),
    }
    if color:
        enc["color"] = alt.Color(f"{color}:N")
        return alt.Chart(df).mark_bar().encode(**enc)
    return alt.Chart(df).mark_bar(color=ACCENT).encode(**enc)


def chart(qid: str, df: pd.DataFrame) -> alt.Chart:
    if qid == "01_revenue_and_margin":
        return (
            alt.Chart(df)
            .mark_line(point=True, color=ACCENT)
            .encode(x=alt.X("month:N", title=None), y=alt.Y("revenue_eur:Q", title="Revenue (EUR)"), tooltip=list(df.columns))
        )
    if qid == "02_on_time_delivery":
        d = df.assign(year=df["year"].astype(str))
        return (
            alt.Chart(d)
            .mark_bar()
            .encode(
                x=alt.X("carrier:N", title=None),
                xOffset="year:N",
                y=alt.Y("on_time_pct:Q", title="On time (%)", scale=alt.Scale(domain=[0, 100])),
                color="year:N",
                tooltip=list(d.columns),
            )
        )
    if qid == "03_abc_analysis":
        d = df.melt("abc_class", ["share_of_products_pct", "share_of_revenue_pct"], "measure", "pct")
        d["measure"] = d["measure"].map(
            {"share_of_products_pct": "Share of products", "share_of_revenue_pct": "Share of revenue"}
        )
        return (
            alt.Chart(d)
            .mark_bar()
            .encode(
                x=alt.X("abc_class:N", title="Class"),
                xOffset="measure:N",
                y=alt.Y("pct:Q", title="%"),
                color="measure:N",
                tooltip=list(d.columns),
            )
        )
    if qid == "04_supplier_scorecard":
        return bar(df, "supplier_id", "late_pct")
    if qid == "05_fill_rate":
        return bar(df, "category", "lost_revenue_eur", color="warehouse_id")
    if qid == "06_stockouts_on_a_items":
        d = df.assign(item=df["sku"] + " · " + df["warehouse_id"])
        return bar(d, "item", "stockout_days", color="supplier_id", horizontal=True)
    if qid == "07_inventory_turns":
        return bar(df, "category", "turns_per_year")
    if qid == "08_abc_xyz_matrix":
        base = alt.Chart(df).encode(
            x=alt.X("xyz_class:N", title="Forecastability (X stable … Z erratic)"), y=alt.Y("abc_class:N", title="Value class")
        )
        heat = base.mark_rect().encode(
            color=alt.Color("share_of_revenue_pct:Q", scale=alt.Scale(scheme="oranges"), title="% of revenue"),
            tooltip=list(df.columns),
        )
        text = base.mark_text(fontSize=14).encode(text="products:Q")
        return heat + text
    if qid == "09_order_cycle_time":
        d = df.melt("city", ["avg_processing_days", "avg_transit_days"], "stage", "days")
        d["stage"] = d["stage"].map({"avg_processing_days": "Warehouse processing", "avg_transit_days": "Carrier transit"})
        return (
            alt.Chart(d)
            .mark_bar()
            .encode(
                y=alt.Y("city:N", title=None),
                x=alt.X("days:Q", stack=True, title="Average days"),
                color="stage:N",
                tooltip=list(d.columns),
            )
        )
    if qid == "10_late_suppliers_and_stockouts":
        base = alt.Chart(df).encode(
            x=alt.X("late_pct:Q", title="Purchase orders delivered late (%)"),
            y=alt.Y("stockout_day_pct:Q", title="Stockout days (%)"),
        )
        return base.mark_circle(size=120, color=ACCENT).encode(tooltip=list(df.columns)) + base.mark_text(
            dx=14, align="left"
        ).encode(text="supplier_id:N")
    raise KeyError(qid)


# ---------------------------------------------------------------------------
st.sidebar.title("Supply Chain SQL Analytics")
page = st.sidebar.radio("Page", ["Overview", "10 business questions", "SQL playground"], label_visibility="collapsed")
st.sidebar.caption("Synthetic data: every company, product and number is invented.")
st.sidebar.markdown("[Source on GitHub](https://github.com/insan-sll/supply-chain-sql-analytics)")

questions = load_questions()

if page == "Overview":
    st.title("Supply Chain SQL Analytics")
    st.write(
        "Two years of operations at a fictional spare-parts distributor: orders, shipments, purchase orders "
        "and daily stock across three warehouses. Ten questions an operations team actually asks, each "
        "answered with one SQL query on DuckDB."
    )
    kpi = run_cached(
        """
        SELECT
          (SELECT SUM(l.qty_shipped * l.unit_price) FROM order_lines l JOIN orders o USING (order_id)
             WHERE year(o.order_date) = 2025)                                         AS revenue_2025,
          (SELECT 100 * SUM(qty_shipped) / SUM(qty_ordered) FROM order_lines)          AS fill_rate,
          (SELECT 100 * AVG(CASE WHEN delivered_date <= promised_date THEN 1 ELSE 0 END) FROM shipments) AS on_time,
          (SELECT 100 * AVG(CASE WHEN received_date > expected_date THEN 1 ELSE 0 END)
             FROM purchase_orders WHERE received_date IS NOT NULL)                     AS supplier_late
        """
    ).iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Revenue 2025", f"€{kpi['revenue_2025'] / 1e6:.2f} M")
    c2.metric("Fill rate", f"{kpi['fill_rate']:.1f} %")
    c3.metric("On-time delivery", f"{kpi['on_time']:.1f} %")
    c4.metric("Late purchase orders", f"{kpi['supplier_late']:.1f} %")

    st.subheader("Data model")
    counts = run_cached(" UNION ALL ".join(f"SELECT '{t}' AS table_name, COUNT(*) AS row_count FROM {t}" for t in TABLES))
    counts["description"] = counts["table_name"].map(TABLES)
    st.dataframe(counts, hide_index=True, width="stretch")
    st.caption(
        "Keys and CHECK constraints are declared in sql/schema.sql, so inconsistent data fails on load. "
        "The ABC classification is a reusable view (sql/views.sql)."
    )

    st.subheader("How the data is made")
    st.write(
        "A seeded Python generator simulates customer orders with seasonality, a reorder-point policy per "
        "product and warehouse, supplier delays and carrier transit times. Some patterns are built in on "
        "purpose (one unreliable supplier, one weak carrier, one slow warehouse), so the queries have "
        "something real to find. The queries don't know about them: they find them from the data alone."
    )

elif page == "10 business questions":
    titles = [f"{i}. {q.title}" for i, q in enumerate(questions, start=1)]
    choice = st.sidebar.selectbox("Question", range(len(questions)), format_func=lambda i: titles[i])
    q = questions[choice]
    st.title(titles[choice])
    st.markdown(f"**Question:** {q.question}")
    st.markdown(f"**Method:** {q.method}")
    df = run_cached(q.sql)
    st.info(finding(q.id, df))
    st.altair_chart(chart(q.id, df), width="stretch")
    with st.expander("SQL", expanded=True):
        st.code(q.sql, language="sql")
    st.dataframe(df, hide_index=True, width="stretch")

else:
    st.title("SQL playground")
    st.write(
        f"Write your own SELECT against the same database. It is opened read-only; results are capped at {MAX_ROWS} rows. "
        "Tables: " + ", ".join(f"`{t}`" for t in TABLES) + ", plus the view `product_abc`."
    )
    default = (
        "SELECT p.category,\n"
        "       COUNT(DISTINCT p.product_id) AS products,\n"
        "       ROUND(SUM(l.qty_shipped * l.unit_price)) AS revenue_eur\n"
        "FROM order_lines l\n"
        "JOIN products p USING (product_id)\n"
        "GROUP BY p.category\n"
        "ORDER BY revenue_eur DESC"
    )
    sql = st.text_area("SQL", default, height=220)
    if st.button("Run query", type="primary"):
        try:
            result = run(prepare(sql))
        except QueryRejected as exc:
            st.warning(str(exc))
        except duckdb.Error as exc:
            st.error(f"Query failed: {exc}")
        else:
            st.caption(f"{len(result)} rows")
            st.dataframe(result, hide_index=True, width="stretch")
