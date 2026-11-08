from scsql.generate import generate


def test_generator_is_deterministic():
    a, b = generate(seed=3), generate(seed=3)
    for name in a:
        assert a[name].equals(b[name]), name


def test_row_counts_are_plausible(con):
    counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("orders", "order_lines", "products")}
    assert counts["products"] == 200
    assert 20_000 < counts["orders"] < 40_000
    assert counts["order_lines"] > counts["orders"]


def test_shipped_never_exceeds_ordered(con):
    assert con.execute("SELECT COUNT(*) FROM order_lines WHERE qty_shipped > qty_ordered").fetchone()[0] == 0


def test_stock_never_negative(con):
    assert con.execute("SELECT MIN(on_hand) FROM inventory_daily").fetchone()[0] >= 0


def test_every_order_with_shipped_units_has_a_shipment(con):
    missing = con.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT order_id FROM order_lines GROUP BY order_id HAVING SUM(qty_shipped) > 0
        ) o LEFT JOIN shipments s USING (order_id) WHERE s.order_id IS NULL
        """
    ).fetchone()[0]
    assert missing == 0


def test_constraints_reject_bad_rows(con):
    import duckdb
    import pytest

    with pytest.raises(duckdb.ConstraintException):
        con.execute("INSERT INTO order_lines VALUES (1, 99, 1, 5, 6, 1.0)")  # shipped > ordered
