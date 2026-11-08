-- title: Inventory turns and days of inventory (2025)
-- question: How fast does stock move in each category, and how many days of demand are we holding?
-- method: Divide 2025 cost of goods sold by the average daily inventory value at cost; days of inventory is 365 divided by turns.
WITH cogs AS (
    SELECT p.category, SUM(l.qty_shipped * p.unit_cost) AS cogs
    FROM order_lines l
    JOIN orders   o USING (order_id)
    JOIN products p USING (product_id)
    WHERE year(o.order_date) = 2025
    GROUP BY 1
),
stock AS (
    SELECT p.category,
           SUM(i.on_hand * p.unit_cost) / COUNT(DISTINCT i.snapshot_date) AS avg_inventory_value
    FROM inventory_daily i
    JOIN products p USING (product_id)
    WHERE year(i.snapshot_date) = 2025
    GROUP BY 1
)
SELECT category,
       ROUND(avg_inventory_value, 0)              AS avg_inventory_value_eur,
       ROUND(cogs, 0)                             AS cogs_eur,
       ROUND(cogs / avg_inventory_value, 1)       AS turns_per_year,
       ROUND(365 * avg_inventory_value / cogs, 0) AS days_of_inventory
FROM cogs
JOIN stock USING (category)
ORDER BY turns_per_year DESC;
