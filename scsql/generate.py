"""Seeded generator for a synthetic B2B spare-parts distributor.

Every supplier, product, carrier and number here is invented. The generator
simulates two years of orders, an (s, Q) reorder policy per product and
warehouse, purchase orders with supplier delays, and outbound shipments.

A few patterns are built in on purpose so the SQL has something real to find:
one unreliable supplier (S07), a fourth-quarter demand peak, one slower and less
predictable carrier, and one slower warehouse.
"""

from __future__ import annotations

import math
from collections import defaultdict

import numpy as np
import pandas as pd

START = pd.Timestamp("2024-01-01")
DAYS = 731  # 2024 (a leap year) and 2025
SEED = 7
N_PRODUCTS = 200

# category: (median unit cost in EUR, typical order quantity, share of SKUs)
CATEGORIES: dict[str, tuple[float, int, float]] = {
    "Fasteners": (0.9, 40, 0.30),
    "Bearings": (14.0, 6, 0.20),
    "Electronics": (28.0, 4, 0.20),
    "Hydraulics": (65.0, 2, 0.15),
    "Packaging": (1.6, 25, 0.15),
}

# supplier_id, country, category, promised lead days, late probability, mean days late
SUPPLIERS: list[tuple[str, str, str, int, float, float]] = [
    ("S01", "DE", "Fasteners", 10, 0.08, 2),
    ("S02", "PL", "Fasteners", 14, 0.12, 3),
    ("S03", "CZ", "Bearings", 12, 0.06, 2),
    ("S04", "IT", "Bearings", 18, 0.10, 3),
    ("S05", "DE", "Electronics", 14, 0.07, 2),
    ("S06", "TW", "Electronics", 35, 0.15, 4),
    ("S07", "TR", "Hydraulics", 21, 0.55, 14),  # the unreliable supplier
    ("S08", "DE", "Hydraulics", 16, 0.08, 2),
    ("S09", "PL", "Packaging", 7, 0.05, 1),
    ("S10", "NL", "Packaging", 9, 0.10, 2),
    ("S11", "CN", "Fasteners", 42, 0.18, 5),
    ("S12", "AT", "Electronics", 12, 0.06, 2),
]

WAREHOUSES = [("W1", "Augsburg"), ("W2", "Hamburg"), ("W3", "Leipzig")]
REGION_SHARE = {"South": 0.35, "West": 0.20, "North": 0.25, "East": 0.20}
REGION_WAREHOUSE = {"South": "W1", "West": "W1", "North": "W2", "East": "W3"}

# carrier: (mean transit days, standard deviation, share of shipments)
CARRIERS = {
    "Carrier A": (1.6, 0.6, 0.45),
    "Carrier B": (2.0, 0.9, 0.35),
    "Carrier C": (2.4, 1.6, 0.20),
}
# warehouse: processing days, sampled uniformly (W3 is the slow one)
PROCESSING = {"W1": [0, 1, 1, 1, 2], "W2": [0, 1, 1, 2, 2], "W3": [1, 1, 2, 2, 3]}
PROMISE_DAYS = 4  # delivery promised four days after the order
SERVICE_Z = 2.05  # safety-stock factor, about a 98 % cycle service level
ORDER_COVER_DAYS = 30  # each purchase order covers about a month of demand


def generate(seed: int = SEED) -> dict[str, pd.DataFrame]:
    """Return every table as a DataFrame. Same seed, same data."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range(START, periods=DAYS, freq="D")
    wh_ids = [w[0] for w in WAREHOUSES]

    suppliers = pd.DataFrame(
        [(s[0], s[1], s[3]) for s in SUPPLIERS],
        columns=["supplier_id", "country", "promised_lead_days"],
    )
    sup_info = {s[0]: s for s in SUPPLIERS}
    warehouses = pd.DataFrame(WAREHOUSES, columns=["warehouse_id", "city"])

    # ---- products -------------------------------------------------------
    cats = list(CATEGORIES)
    shares = np.array([CATEGORIES[c][2] for c in cats])
    product_cat = np.array(cats)[rng.choice(len(cats), size=N_PRODUCTS, p=shares / shares.sum())]
    sup_by_cat = {c: [s[0] for s in SUPPLIERS if s[2] == c] for c in cats}
    product_sup = np.array([rng.choice(sup_by_cat[c]) for c in product_cat])
    median_cost = np.array([CATEGORIES[c][0] for c in product_cat])
    unit_cost = np.round(median_cost * rng.lognormal(0, 0.45, N_PRODUCTS), 2).clip(0.05)
    unit_price = np.round(unit_cost * rng.uniform(1.25, 1.75, N_PRODUCTS), 2)
    products = pd.DataFrame(
        {
            "product_id": np.arange(1, N_PRODUCTS + 1),
            "sku": [f"SKU-{i:04d}" for i in range(1, N_PRODUCTS + 1)],
            "category": product_cat,
            "supplier_id": product_sup,
            "unit_cost": unit_cost,
            "unit_price": unit_price,
        }
    )

    # ---- demand shape ---------------------------------------------------
    popularity = rng.lognormal(0, 1.3, N_PRODUCTS)  # long tail, so ABC is meaningful
    cv = rng.choice([0.2, 0.6, 1.4], size=N_PRODUCTS, p=[0.4, 0.35, 0.25])  # drives XYZ
    typical_qty = np.array([CATEGORIES[c][1] for c in product_cat]) * rng.uniform(0.6, 1.4, N_PRODUCTS)
    doy = dates.dayofyear.to_numpy()
    season = 1 + 0.25 * np.cos(2 * np.pi * (doy - 330) / 365.25)  # peak in late November
    trend = np.where(dates.year == 2025, 1.08, 1.0)
    weekday = np.where(dates.dayofweek >= 5, 0.25, 1.0)
    orders_per_day = rng.poisson(48 * season * trend * weekday)
    week = np.arange(DAYS) // 7
    shape = 1 / cv**2
    weekly_noise = rng.gamma(shape, 1 / shape, size=(week.max() + 1, N_PRODUCTS))
    day_weights = popularity * weekly_noise[week]

    # ---- orders and lines -----------------------------------------------
    regions = list(REGION_SHARE)
    region_p = list(REGION_SHARE.values())
    order_day, order_region, line_rows = [], [], []
    for d in range(DAYS):
        n = orders_per_day[d]
        if n == 0:
            continue
        p = day_weights[d] / day_weights[d].sum()
        reg = rng.choice(len(regions), size=n, p=region_p)
        n_lines = np.minimum(1 + rng.poisson(1.3, size=n), 5)
        for k in range(n):
            order_day.append(d)
            order_region.append(regions[reg[k]])
            oid = len(order_day)
            prods = rng.choice(N_PRODUCTS, size=n_lines[k], replace=False, p=p)
            qtys = np.maximum(1, rng.poisson(typical_qty[prods]))
            for ln, (pi, q) in enumerate(zip(prods, qtys, strict=True), start=1):
                line_rows.append((oid, ln, pi, q))

    order_day_a = np.array(order_day)
    order_wh = np.array([REGION_WAREHOUSE[r] for r in order_region])
    lines = np.array(line_rows)
    line_oid, line_prod, line_qty = lines[:, 0], lines[:, 2], lines[:, 3]
    line_day = order_day_a[line_oid - 1]
    line_wh = np.array([wh_ids.index(w) for w in order_wh])[line_oid - 1]
    shipped = np.zeros(len(lines), dtype=int)

    # ---- inventory simulation: (s, Q) policy per product and warehouse ----
    key = line_prod * len(wh_ids) + line_wh
    order = np.lexsort((np.arange(len(lines)), line_day, key))
    keys_sorted = key[order]
    bounds = np.flatnonzero(np.diff(keys_sorted)) + 1
    groups = np.split(order, bounds)

    stock_blocks, po_rows = [], []
    for idxs in groups:
        pi, wi = divmod(int(key[idxs[0]]), len(wh_ids))
        sup = product_sup[pi]
        _, _, _, promised, late_p, late_mean = sup_info[sup]
        days, qty = line_day[idxs], line_qty[idxs]
        daily = np.bincount(days, weights=qty, minlength=DAYS)
        avg, sigma = daily.mean(), daily.std()
        # Planned with the promised lead time: late deliveries are what hurts.
        safety = SERVICE_Z * sigma * math.sqrt(promised)
        reorder_point = math.ceil(avg * promised + safety)
        order_qty = max(1, math.ceil(avg * ORDER_COVER_DAYS))
        on_hand = reorder_point + order_qty // 2
        open_qty = 0
        arrivals: dict[int, int] = defaultdict(int)
        stock = np.empty(DAYS, dtype=int)
        j, n = 0, len(idxs)
        for d in range(DAYS):
            if d in arrivals:
                received = arrivals.pop(d)
                on_hand += received
                open_qty -= received
            while j < n and days[j] == d:
                take = min(int(qty[j]), on_hand)
                shipped[idxs[j]] = take
                on_hand -= take
                j += 1
            stock[d] = on_hand
            if on_hand + open_qty <= reorder_point:
                if rng.random() < late_p:
                    delay = max(1, round(rng.exponential(late_mean)))
                else:
                    delay = int(rng.integers(-2, 1))  # on time or up to two days early
                arrive = d + promised + delay
                po_rows.append((sup, pi + 1, wh_ids[wi], order_qty, d, d + promised, arrive if arrive < DAYS else None))
                if arrive < DAYS:
                    arrivals[arrive] += order_qty
                open_qty += order_qty
        stock_blocks.append((pi + 1, wh_ids[wi], stock))

    def to_date(day_index) -> pd.Series:
        return START + pd.to_timedelta(pd.Series(day_index, dtype="float64"), unit="D")

    orders = pd.DataFrame(
        {
            "order_id": np.arange(1, len(order_day_a) + 1),
            "order_date": to_date(order_day_a),
            "region": order_region,
            "warehouse_id": order_wh,
        }
    )
    order_lines = pd.DataFrame(
        {
            "order_id": line_oid,
            "line_no": lines[:, 1],
            "product_id": line_prod + 1,
            "qty_ordered": line_qty,
            "qty_shipped": shipped,
            "unit_price": unit_price[line_prod],
        }
    )

    # ---- outbound shipments (orders with at least one unit shipped) -----
    units = np.bincount(line_oid, weights=shipped, minlength=len(order_day_a) + 1)[1:]
    has_ship = units > 0
    n_ship = int(has_ship.sum())
    ship_wh = order_wh[has_ship]
    processing = np.zeros(n_ship, dtype=int)
    for w, options in PROCESSING.items():
        mask = ship_wh == w
        processing[mask] = rng.choice(options, size=int(mask.sum()))
    carrier_names = list(CARRIERS)
    carrier_idx = rng.choice(len(carrier_names), size=n_ship, p=[c[2] for c in CARRIERS.values()])
    means = np.array([CARRIERS[c][0] for c in carrier_names])[carrier_idx]
    sds = np.array([CARRIERS[c][1] for c in carrier_names])[carrier_idx]
    transit = np.maximum(1, np.round(rng.normal(means, sds))).astype(int)
    ship_order_day = order_day_a[has_ship]
    shipments = pd.DataFrame(
        {
            "order_id": np.flatnonzero(has_ship) + 1,
            "carrier": np.array(carrier_names)[carrier_idx],
            "shipped_date": to_date(ship_order_day + processing),
            "promised_date": to_date(ship_order_day + PROMISE_DAYS),
            "delivered_date": to_date(ship_order_day + processing + transit),
        }
    )

    purchase_orders = pd.DataFrame(
        po_rows,
        columns=["supplier_id", "product_id", "warehouse_id", "qty", "order_day", "expected_day", "received_day"],
    )
    purchase_orders.insert(0, "po_id", np.arange(1, len(purchase_orders) + 1))
    purchase_orders["order_date"] = to_date(purchase_orders.pop("order_day"))
    purchase_orders["expected_date"] = to_date(purchase_orders.pop("expected_day"))
    purchase_orders["received_date"] = to_date(purchase_orders.pop("received_day"))

    inventory_daily = pd.DataFrame(
        {
            "snapshot_date": np.tile(dates.to_numpy(), len(stock_blocks)),
            "warehouse_id": np.repeat([b[1] for b in stock_blocks], DAYS),
            "product_id": np.repeat([b[0] for b in stock_blocks], DAYS),
            "on_hand": np.concatenate([b[2] for b in stock_blocks]),
        }
    )

    return {
        "suppliers": suppliers,
        "warehouses": warehouses,
        "products": products,
        "orders": orders,
        "order_lines": order_lines,
        "shipments": shipments,
        "purchase_orders": purchase_orders,
        "inventory_daily": inventory_daily,
    }
