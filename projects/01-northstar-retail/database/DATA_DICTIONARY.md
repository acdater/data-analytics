# Data Dictionary

All monetary values use `NUMERIC` with two decimal places. Primary keys are integer identifiers. Foreign keys are enforced by PostgreSQL. Nullable values are called out below; fields not marked nullable are required.

## `categories`

| Column | Meaning |
| --- | --- |
| `category_id` | Primary key. |
| `category_name` | Unique product category label. |
| `description` | Short category description. |

## `customers`

| Column | Meaning |
| --- | --- |
| `customer_id` | Primary key. |
| `email` | Unique contact value. |
| `first_name`, `last_name` | Customer name. |
| `signup_date` | Date the account was created. |
| `city`, `state_code` | Customer location. |
| `phone` | Phone contact; nullable. |
| `loyalty_tier` | `standard`, `plus`, or `vip`. |

## `products`

| Column | Meaning |
| --- | --- |
| `product_id` | Primary key. |
| `category_id` | Foreign key to `categories`. |
| `sku` | Unique stock-keeping unit. |
| `product_name` | Catalog product name. |
| `list_price`, `unit_cost` | Current catalog price and unit cost. |
| `is_active` | Whether the product is currently active. |

## `orders`

| Column | Meaning |
| --- | --- |
| `order_id` | Primary key. |
| `customer_id` | Foreign key to `customers`. |
| `order_ts` | UTC order timestamp. |
| `order_status` | `pending`, `paid`, `shipped`, `delivered`, or `cancelled`. |
| `subtotal` | Sum of item quantities multiplied by their unit prices, before discounts. |
| `discount_amount` | Sum of line discounts. |
| `tax_amount` | Tax on the discounted merchandise subtotal. |
| `shipping_fee` | Shipping charged on the order. |
| `total_amount` | Subtotal less discounts, plus tax and shipping. |

## `order_items`

| Column | Meaning |
| --- | --- |
| `order_item_id` | Primary key. |
| `order_id` | Foreign key to `orders`. |
| `product_id` | Foreign key to `products`. |
| `quantity` | Units ordered. |
| `unit_price`, `unit_cost` | Historical per-unit price and cost snapshots. |
| `line_subtotal` | Quantity multiplied by unit price, before discount. |
| `discount_amount` | Discount applied to this line. |
| `discount_code` | Applied code; nullable. |

## `payments`

| Column | Meaning |
| --- | --- |
| `payment_id` | Primary key. |
| `order_id` | Foreign key to `orders`. |
| `payment_type` | `charge`, `refund`, or `void`. |
| `payment_status` | `pending`, `captured`, `refunded`, or `voided`. |
| `amount` | Non-negative payment event amount. Void events have amount zero. |
| `payment_ts` | UTC payment event timestamp. |
| `transaction_ref` | Unique synthetic transaction reference. |

## `returns`

| Column | Meaning |
| --- | --- |
| `return_id` | Primary key. |
| `order_item_id` | Foreign key to the returned `order_items` row. |
| `refund_payment_id` | Unique foreign key to the associated refund in `payments`. |
| `return_date` | Date the return was recorded. |
| `quantity` | Units returned. |
| `refund_amount` | Refund including allocated tax; shipping is not refunded. |
| `return_status` | `approved`, `refunded`, or `rejected`. |

## `marketing_spend`

| Column | Meaning |
| --- | --- |
| `marketing_spend_id` | Primary key. |
| `spend_month` | First day of the month represented. |
| `source`, `campaign_name` | Marketing source and campaign label. |
| `spend_amount` | Spend for the source and month. |
| `impressions`, `clicks` | Non-negative campaign delivery counts; clicks cannot exceed impressions. |