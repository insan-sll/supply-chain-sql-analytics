-- title: Revenue and gross margin by month
-- question: How are revenue and gross margin developing, and how fast is the business growing month over month?
-- method: Aggregate shipped revenue and cost of goods per month, then compare each month with the one before using LAG.
WITH monthly AS (
    SELECT date_trunc('month', o.order_date)  AS month,
           SUM(l.qty_shipped * l.unit_price)  AS revenue,
           SUM(l.qty_shipped * p.unit_cost)   AS cogs
    FROM order_lines l
    JOIN orders   o USING (order_id)
    JOIN products p USING (product_id)
    GROUP BY 1
)
SELECT strftime(month, '%Y-%m')                                        AS month,
       ROUND(revenue, 0)                                               AS revenue_eur,
       ROUND(100 * (revenue - cogs) / revenue, 1)                      AS gross_margin_pct,
       ROUND(100 * (revenue / LAG(revenue) OVER (ORDER BY month) - 1), 1) AS mom_growth_pct,
       ROUND(100 * (revenue / LAG(revenue, 12) OVER (ORDER BY month) - 1), 1) AS yoy_growth_pct
FROM monthly
ORDER BY month;
