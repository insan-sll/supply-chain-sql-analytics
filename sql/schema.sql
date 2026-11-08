-- Schema for a synthetic B2B spare-parts distributor.
-- Keys and checks are declared so bad data fails on load instead of in a report.

CREATE TABLE suppliers (
    supplier_id        VARCHAR PRIMARY KEY,
    country            VARCHAR NOT NULL,
    promised_lead_days INTEGER NOT NULL CHECK (promised_lead_days > 0)
);

CREATE TABLE warehouses (
    warehouse_id VARCHAR PRIMARY KEY,
    city         VARCHAR NOT NULL
);

CREATE TABLE products (
    product_id  INTEGER PRIMARY KEY,
    sku         VARCHAR NOT NULL UNIQUE,
    category    VARCHAR NOT NULL,
    supplier_id VARCHAR NOT NULL REFERENCES suppliers (supplier_id),
    unit_cost   DOUBLE  NOT NULL CHECK (unit_cost > 0),
    unit_price  DOUBLE  NOT NULL CHECK (unit_price >= unit_cost)
);

CREATE TABLE orders (
    order_id     INTEGER PRIMARY KEY,
    order_date   DATE    NOT NULL,
    region       VARCHAR NOT NULL,
    warehouse_id VARCHAR NOT NULL REFERENCES warehouses (warehouse_id)
);

CREATE TABLE order_lines (
    order_id    INTEGER NOT NULL REFERENCES orders (order_id),
    line_no     INTEGER NOT NULL,
    product_id  INTEGER NOT NULL REFERENCES products (product_id),
    qty_ordered INTEGER NOT NULL CHECK (qty_ordered > 0),
    qty_shipped INTEGER NOT NULL CHECK (qty_shipped BETWEEN 0 AND qty_ordered),
    unit_price  DOUBLE  NOT NULL,
    PRIMARY KEY (order_id, line_no)
);

CREATE TABLE shipments (
    order_id       INTEGER PRIMARY KEY REFERENCES orders (order_id),
    carrier        VARCHAR NOT NULL,
    shipped_date   DATE    NOT NULL,
    promised_date  DATE    NOT NULL,
    delivered_date DATE    NOT NULL CHECK (delivered_date >= shipped_date)
);

CREATE TABLE purchase_orders (
    po_id         INTEGER PRIMARY KEY,
    supplier_id   VARCHAR NOT NULL REFERENCES suppliers (supplier_id),
    product_id    INTEGER NOT NULL REFERENCES products (product_id),
    warehouse_id  VARCHAR NOT NULL REFERENCES warehouses (warehouse_id),
    qty           INTEGER NOT NULL CHECK (qty > 0),
    order_date    DATE    NOT NULL,
    expected_date DATE    NOT NULL,
    received_date DATE    -- NULL while the purchase order is still open
);

CREATE TABLE inventory_daily (
    snapshot_date DATE    NOT NULL,
    warehouse_id  VARCHAR NOT NULL REFERENCES warehouses (warehouse_id),
    product_id    INTEGER NOT NULL REFERENCES products (product_id),
    on_hand       INTEGER NOT NULL CHECK (on_hand >= 0),
    PRIMARY KEY (snapshot_date, warehouse_id, product_id)
);
