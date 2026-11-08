-- title: On-time delivery by carrier
-- question: Which carrier keeps the delivery promise to customers, and how late are the late ones?
-- method: Compare the delivered date with the promised date per shipment, split by carrier and order year.
SELECT s.carrier,
       year(o.order_date)                                               AS year,
       COUNT(*)                                                         AS shipments,
       ROUND(100 * AVG(CASE WHEN delivered_date <= promised_date THEN 1 ELSE 0 END), 1) AS on_time_pct,
       ROUND(AVG(date_diff('day', promised_date, delivered_date))
             FILTER (WHERE delivered_date > promised_date), 1)          AS avg_days_late_when_late
FROM shipments s
JOIN orders o USING (order_id)
GROUP BY ALL
ORDER BY s.carrier, year;
