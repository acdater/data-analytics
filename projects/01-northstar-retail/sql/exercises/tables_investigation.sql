SELECT table_name AS "Table Name", table_catalog AS "Table  Catalog"
FROM information_schema.tables
WHERE table_schema = 'public'
	AND table_type = 'BASE TABLE'
ORDER BY table_name

SELECT COUNT(*)
FROM customers

SELECT COUNT(*)
FROM orders

SELECT MIN(order_ts)
FROM orders

SELECT * 
FROM orders
WHERE order_ts = (SELECT MIN(order_ts)FROM orders) OR 
	order_ts = (SELECT MAX(order_ts) FROM orders)
ORDER BY order_ts

SELECT
    MIN(order_ts) AS first_order,
    MAX(order_ts) AS last_order
FROM orders;

SELECT order_status as "Status", COUNT(*) as "Count"
FROM orders
GROUP BY order_status
ORDER BY "Count"

SELECT c.category_name, COUNT(p.product_id)
FROM products as p
INNER JOIN categories as c ON p.category_id = c.category_id
GROUP BY c.category_name

SELECT c.category_name, COUNT(p.product_id) as product_count
FROM products as p
RIGHT JOIN categories as c ON p.category_id = c.category_id
GROUP BY c.category_id, c.category_name
ORDER BY product_count DESC, c.category_name ASC