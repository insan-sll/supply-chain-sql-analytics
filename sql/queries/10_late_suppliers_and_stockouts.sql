-- title: Do late suppliers cause stockouts?
-- question: Is there a link between how often a supplier delivers late and how often its products are out of stock?
-- method: Join the late share per supplier with the share of stockout days of its products, and compute the correlation across suppliers.
WITH lateness AS (
    SELECT supplier_id,
           100 * AVG(CASE WHEN received_date > expected_date THEN 1 ELSE 0 END) AS late_pct
    FROM purchase_orders
    WHERE received_date IS NOT NULL
    GROUP BY supplier_id
),
stockouts AS (
    SELECT p.supplier_id,
           100 * AVG(CASE WHEN i.on_hand = 0 THEN 1 ELSE 0 END) AS stockout_day_pct
    FROM inventory_daily i
    JOIN products p USING (product_id)
    GROUP BY p.supplier_id
)
SELECT supplier_id,
       ROUND(late_pct, 1)                                       AS late_pct,
       ROUND(stockout_day_pct, 2)                               AS stockout_day_pct,
       ROUND(corr(late_pct, stockout_day_pct) OVER (), 2)       AS correlation_across_suppliers
FROM lateness
JOIN stockouts USING (supplier_id)
ORDER BY late_pct DESC;
