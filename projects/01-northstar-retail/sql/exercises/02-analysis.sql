-- select  c.state_code, count(*) as orders_count
-- from orders as o
-- INNER JOIN customers as c on o.customer_id = c.customer_id
-- GROUP BY c.state_code
-- ORDER BY orders_count DESC
-- LIMIT 5

-- select c.category_name, SUM(oi.quantity) as units_sold
-- from order_items as oi
-- inner join products as p on oi.product_id = p.product_id
-- inner join categories as c on p.category_id = c.category_id
-- group by c.category_name
-- order by units_sold DESC
-- limit 5

-- SELECT
--     COUNT(*) AS total_rows,
--     COUNT(DISTINCT p.product_id) AS unique_products,
--     COUNT(DISTINCT c.category_id) AS unique_categories
-- FROM order_items AS oi
-- INNER JOIN products AS p
--     ON oi.product_id = p.product_id
-- INNER JOIN categories AS c
--     ON p.category_id = c.category_id;

-- select c.category_name, sum(oi.line_subtotal) as total
-- from order_items as oi
-- inner join products as p on oi.product_id = p.product_id
-- inner join categories as c on p.category_id = c.category_id
-- group by c.category_name
-- order by total desc
-- limit 5

-- SELECT COUNT(*) AS mismatch_count
-- FROM order_items
-- WHERE line_subtotal IS DISTINCT FROM quantity * unit_price;

-- select 
-- 	c.category_name												as category_name, 
-- 	sum(oi.line_subtotal)										as gross_sales, 
-- 	sum(oi.discount_amount)										as total_discounts, 
-- 	(sum(oi.line_subtotal)- sum(oi.discount_amount))			as net_sales,
-- 	round(
-- 		sum(oi.discount_amount) 
-- 		/ nullif(sum(oi.line_subtotal),0) * 100,2)				as discount_rate
-- from order_items as oi 
-- inner join products as p on oi.product_id = p.product_id
-- inner join categories as c on p.category_id = c.category_id
-- group by c.category_name
-- order by net_sales DESC

-- select 
-- 	c.category_name,
-- 	sum(oi.line_subtotal) - sum(oi.discount_amount) as net_sales_before_return,
-- 	sum(oi.quantity * oi.unit_cost) 				as cogs,
-- 	sum(oi.line_subtotal) - sum(oi.discount_amount) 
-- 		- sum(oi.quantity * oi.unit_cost)			as gross_profit,
-- 	round(
-- 		(sum(oi.line_subtotal) - sum(oi.discount_amount) 
-- 			- sum(oi.quantity * oi.unit_cost)) 
-- 				/ nullif((sum(oi.line_subtotal) - sum(oi.discount_amount)),0)	
-- 				* 100,
-- 		2)											as gross_margin_pct
-- from order_items as oi
-- inner join products as p on oi.product_id = p.product_id
-- inner join categories as c on p.category_id = c.category_id
-- group by c.category_name
-- order by gross_profit desc

-- WITH category_financials AS (
--     SELECT
--         c.category_name,
--         SUM(oi.line_subtotal - oi.discount_amount) AS net_sales,
--         SUM(oi.quantity * oi.unit_cost) AS cogs
--     FROM order_items AS oi
--     JOIN products AS p
--         ON oi.product_id = p.product_id
--     JOIN categories AS c
--         ON p.category_id = c.category_id
--     GROUP BY c.category_id, c.category_name
-- )
-- SELECT
--     category_name,
--     net_sales,
--     cogs,
--     net_sales - cogs AS gross_profit,
--     ROUND(
--         (net_sales - cogs)
--         / NULLIF(net_sales, 0) * 100,
--         2
--     ) AS gross_margin_pct
-- FROM category_financials
-- ORDER BY gross_profit DESC;

-- with monthly_data as (
-- 	select
-- 		order_id,
-- 		date_trunc('month', order_ts)							as date
-- 	from orders
-- ),
-- financials as (
-- 	select 
-- 		order_id,
-- 		sum (quantity * unit_cost)								as cogs_tmp,
-- 		sum(line_subtotal - discount_amount)					as net_sales_tmp
-- 	from order_items
-- 	group by order_id
-- )
-- select
-- 	date,
-- 	sum(net_sales_tmp)													as net_sales,
-- 	sum(cogs_tmp)														as cogs,
-- 	sum(net_sales_tmp - cogs_tmp)										as gross_profit,
-- 	round(
-- 			sum(net_sales_tmp - cogs_tmp)
-- 			/ nullif(sum(net_sales_tmp),0) * 100,
-- 		2)																as gross_margin_pct
-- from monthly_data as md
-- join financials as f on md.order_id = f.order_id
-- group by date
-- order by date DESC
-- limit 24

-- SELECT
--     MIN(order_ts) AS first_order_date,
--     MAX(order_ts) AS last_order_date,
--     COUNT(DISTINCT DATE_TRUNC('month', order_ts)) AS months_with_orders
-- FROM orders;

with monthly_data as (
	select
		order_id,
		date_trunc('month', order_ts)							as date
	from orders
),
financials as (
	select 
		order_id,
		sum (quantity * unit_cost)								as cogs_tmp,
		sum(line_subtotal - discount_amount)					as net_sales_tmp
	from order_items
	group by order_id
),
monthly_results as (
	select
		date,
		extract(month from date)								as month,
		extract(year from date)									as year,
		sum(net_sales_tmp)										as net_sales,
		sum(cogs_tmp)											as cogs,
		sum(net_sales_tmp - cogs_tmp)							as gross_profit,
		round(
				sum(net_sales_tmp - cogs_tmp)
				/ nullif(sum(net_sales_tmp),0) * 100,
			2)													as gross_margin_pct
	from monthly_data as md
	join financials as f on md.order_id = f.order_id
	group by date
)
select 
	month,
	max(case when year = 2024 then gross_margin_pct end)	as margin_2024,
	max(case when year = 2025 then gross_margin_pct end)	as margin_2025,
	max(case when year = 2025 then gross_margin_pct end) 
		- max(case when year = 2024 then gross_margin_pct end)	as change_pp
from monthly_results
group by month
order by month ASC