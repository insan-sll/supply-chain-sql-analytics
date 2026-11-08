-- title: ABC analysis of the product range
-- question: How concentrated is revenue? Which share of products earns 80 % of it?
-- method: Rank products by revenue and classify them by cumulative revenue share (view product_abc), then summarise each class.
SELECT abc_class,
       COUNT(*)                                                   AS products,
       ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)           AS share_of_products_pct,
       ROUND(SUM(revenue), 0)                                     AS revenue_eur,
       ROUND(100 * SUM(revenue) / SUM(SUM(revenue)) OVER (), 1)   AS share_of_revenue_pct
FROM product_abc
GROUP BY abc_class
ORDER BY abc_class;
