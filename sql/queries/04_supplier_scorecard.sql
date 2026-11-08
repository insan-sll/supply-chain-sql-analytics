-- title: Supplier scorecard
-- question: Which suppliers deliver late, how often, and by how much compared with what they promised?
-- method: For every received purchase order compare the received date with the expected date, aggregate per supplier and rank by late share.
WITH received AS (
    SELECT po.supplier_id,
           date_diff('day', po.order_date, po.received_date)    AS actual_lead_days,
           date_diff('day', po.expected_date, po.received_date) AS days_late
    FROM purchase_orders po
    WHERE po.received_date IS NOT NULL
),
scored AS (
    SELECT r.supplier_id, s.country, s.promised_lead_days,
           COUNT(*)                                             AS purchase_orders,
           AVG(r.actual_lead_days)                              AS avg_actual_lead_days,
           AVG(CASE WHEN r.days_late > 0 THEN 1 ELSE 0 END)     AS late_share,
           AVG(r.days_late) FILTER (WHERE r.days_late > 0)      AS avg_days_late_when_late
    FROM received r
    JOIN suppliers s USING (supplier_id)
    GROUP BY ALL
)
SELECT RANK() OVER (ORDER BY late_share DESC)  AS worst_rank,
       supplier_id, country, promised_lead_days, purchase_orders,
       ROUND(avg_actual_lead_days, 1)          AS avg_actual_lead_days,
       ROUND(100 * late_share, 1)              AS late_pct,
       ROUND(avg_days_late_when_late, 1)       AS avg_days_late_when_late
FROM scored
ORDER BY worst_rank;
