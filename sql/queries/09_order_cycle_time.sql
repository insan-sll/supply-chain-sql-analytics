-- title: Order cycle time by warehouse
-- question: How long does a customer wait from order to delivery, and where does the time go?
-- method: Median and 90th percentile of order-to-delivery days per warehouse, split into warehouse processing and carrier transit.
SELECT o.warehouse_id,
       w.city,
       COUNT(*)                                                                    AS shipments,
       ROUND(AVG(date_diff('day', o.order_date, s.shipped_date)), 2)               AS avg_processing_days,
       ROUND(AVG(date_diff('day', s.shipped_date, s.delivered_date)), 2)           AS avg_transit_days,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY date_diff('day', o.order_date, s.delivered_date)) AS p50_cycle_days,
       percentile_cont(0.9) WITHIN GROUP (ORDER BY date_diff('day', o.order_date, s.delivered_date)) AS p90_cycle_days,
       ROUND(100 * AVG(CASE WHEN s.delivered_date <= s.promised_date THEN 1 ELSE 0 END), 1) AS on_time_pct
FROM shipments s
JOIN orders     o USING (order_id)
JOIN warehouses w USING (warehouse_id)
GROUP BY ALL
ORDER BY on_time_pct;
