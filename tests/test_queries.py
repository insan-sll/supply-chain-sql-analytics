import pytest

from scsql.findings import finding
from scsql.questions import load_questions

QUESTIONS = load_questions()


def test_ten_questions_with_metadata():
    assert len(QUESTIONS) == 10
    assert all(q.title and q.question and q.method for q in QUESTIONS)


@pytest.mark.parametrize("q", QUESTIONS, ids=lambda q: q.id)
def test_query_returns_rows_and_a_finding(q, results):
    df = results[q.id]
    assert len(df) > 0
    assert finding(q.id, df)


def test_abc_shares_add_up(results):
    df = results["03_abc_analysis"]
    assert df["share_of_revenue_pct"].sum() == pytest.approx(100, abs=0.2)
    assert df["products"].sum() == 200


def test_planted_unreliable_supplier_is_found(results):
    assert results["04_supplier_scorecard"].iloc[0]["supplier_id"] == "S07"


def test_planted_weak_carrier_is_found(results):
    df = results["02_on_time_delivery"]
    assert df.groupby("carrier")["on_time_pct"].mean().idxmin() == "Carrier C"


def test_planted_slow_warehouse_is_found(results):
    assert results["09_order_cycle_time"].iloc[0]["warehouse_id"] == "W3"


def test_lateness_and_stockouts_move_together(results):
    assert results["10_late_suppliers_and_stockouts"]["correlation_across_suppliers"].iloc[0] > 0
