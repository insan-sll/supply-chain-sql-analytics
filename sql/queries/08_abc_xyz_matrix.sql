-- title: ABC-XYZ matrix
-- question: Which products are both important and hard to forecast, and so need the closest planning attention?
-- method: Compute the coefficient of variation of weekly demand per product (weeks without demand count as zero), classify X/Y/Z and cross it with ABC.
WITH weeks AS (
    SELECT DISTINCT date_trunc('week', order_date) AS week FROM orders
),
weekly AS (
    SELECT l.product_id, date_trunc('week', o.order_date) AS week, SUM(l.qty_ordered) AS qty
    FROM order_lines l
    JOIN orders o USING (order_id)
    GROUP BY ALL
),
grid AS (
    SELECT p.product_id, w.week, COALESCE(x.qty, 0) AS qty
    FROM products p
    CROSS JOIN weeks w
    LEFT JOIN weekly x ON x.product_id = p.product_id AND x.week = w.week
),
variability AS (
    SELECT product_id, stddev_samp(qty) / NULLIF(AVG(qty), 0) AS cv
    FROM grid
    GROUP BY product_id
)
SELECT a.abc_class,
       CASE WHEN v.cv <= 0.5 THEN 'X' WHEN v.cv <= 1.0 THEN 'Y' ELSE 'Z' END AS xyz_class,
       COUNT(*)                                                  AS products,
       ROUND(100 * SUM(a.revenue) / SUM(SUM(a.revenue)) OVER (), 1) AS share_of_revenue_pct,
       ROUND(AVG(v.cv), 2)                                       AS avg_cv
FROM product_abc a
JOIN variability v USING (product_id)
GROUP BY ALL
ORDER BY abc_class, xyz_class;
