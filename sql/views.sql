-- Reusable building blocks for the analysis queries.

-- ABC class per product: A = the products that make up the first 80 % of
-- revenue, B = the next 15 %, C = the rest. A product that crosses a boundary
-- belongs to the higher class.
CREATE VIEW product_abc AS
WITH revenue AS (
    SELECT p.product_id, p.sku, p.category, p.supplier_id,
           SUM(l.qty_shipped * l.unit_price) AS revenue
    FROM products p
    LEFT JOIN order_lines l USING (product_id)
    GROUP BY ALL
),
cumulative AS (
    SELECT *,
           SUM(revenue) OVER (ORDER BY revenue DESC, product_id
                              ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)
               / SUM(revenue) OVER () AS share_before
    FROM revenue
)
SELECT product_id, sku, category, supplier_id, revenue,
       CASE WHEN COALESCE(share_before, 0) < 0.80 THEN 'A'
            WHEN share_before < 0.95 THEN 'B'
            ELSE 'C' END AS abc_class
FROM cumulative;
