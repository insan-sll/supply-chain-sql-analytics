-- title: Stockouts on A items
-- question: Which of our most important products ran out of stock most often, and who supplies them?
-- method: Count days with zero stock per A-class product and warehouse, joined with the ABC view and the supplier.
SELECT a.sku,
       a.category,
       a.supplier_id,
       i.warehouse_id,
       COUNT(*) FILTER (WHERE i.on_hand = 0)                       AS stockout_days,
       ROUND(100 * AVG(CASE WHEN i.on_hand = 0 THEN 1 ELSE 0 END), 1) AS stockout_day_pct
FROM inventory_daily i
JOIN product_abc a USING (product_id)
WHERE a.abc_class = 'A'
GROUP BY ALL
HAVING COUNT(*) FILTER (WHERE i.on_hand = 0) > 0
ORDER BY stockout_days DESC, a.sku
LIMIT 15;
