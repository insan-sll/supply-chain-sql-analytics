-- title: Fill rate and lost revenue
-- question: Where can we not ship what customers order, and what does that cost?
-- method: Compare ordered with shipped units per category and warehouse; value the gap at the order price.
SELECT p.category,
       o.warehouse_id,
       SUM(l.qty_ordered)::BIGINT                                  AS units_ordered,
       SUM(l.qty_shipped)::BIGINT                                  AS units_shipped,
       ROUND(100 * SUM(l.qty_shipped) / SUM(l.qty_ordered), 1)     AS fill_rate_pct,
       ROUND(SUM((l.qty_ordered - l.qty_shipped) * l.unit_price), 0) AS lost_revenue_eur
FROM order_lines l
JOIN orders   o USING (order_id)
JOIN products p USING (product_id)
GROUP BY ALL
ORDER BY lost_revenue_eur DESC;
