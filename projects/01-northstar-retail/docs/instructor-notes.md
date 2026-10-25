# Instructor Notes: Northstar Retail

This file is instructor-facing. Do not distribute it with learner materials before the analysis exercise.

## Financial Definitions

- Merchandise gross sales: sum of `order_items.line_subtotal` for non-cancelled orders.
- Merchandise discounts: sum of `order_items.discount_amount` for the same order population.
- Net merchandise sales before returns: gross sales less discounts.
- Refunded merchandise and tax: sum of `returns.refund_amount`; the generated refund includes the returned line's discounted value and allocated tax, but excludes shipping.
- Net sales after returns: net merchandise sales before returns less the refund amount after removing the tax portion where tax-exclusive revenue is required. Since `returns` stores the combined refund, tax must be allocated from the associated order to produce a tax-exclusive measure.
- Captured order cash: `payments.amount` for `payment_type = 'charge'` and `payment_status = 'captured'`; this includes tax and shipping and is not interchangeable with merchandise revenue.
- Product gross profit before returns: net line merchandise sales less `order_items.unit_cost * order_items.quantity`. This excludes operating expenses and marketing spend.
- Marketing spend: `marketing_spend.spend_amount`; it is not included in product gross profit.

Cancelled orders retain their item lines for operational analysis but their payment event is a zero-value void. Exclude them from sales/cash metrics. Pending orders are not captured. Returned orders remain delivered orders and have separate refund events. Discounts and returns are represented at the line level or through linked return/payment records; avoid double-counting when joining tables of different grains.

## Planted Patterns

- Daily transaction volume has a Q4 seasonal lift, especially in November and December, and modest growth through the two-year period.
- Catalog prices rise between the 2024 and 2025 transaction cohorts, while costs rise faster; the historical line snapshots therefore produce lower product margin in 2025.
- Discounts are more frequent in 2025, with deeper discounts in some transactions.
- Customer purchasing propensity is intentionally uneven, producing repeat buyers alongside many lower-frequency customers.
- Cancellations and returns are present; returns occur on a subset of delivered orders and are linked to corresponding refund payments.
- Marketing spend has monthly seasonality and modest growth.

## Planted Data-Quality Anomalies

- Three customer emails have malformed formatting (IDs 17, 821, and 2701); the values remain unique and non-null.
- Two customer rows have an empty string for `city` (IDs 1042 and 3490), not SQL `NULL`.
- One monthly campaign row uses source `Unattributed` while its campaign label retains the original source name.
- A very small number of order lines use discount code `MYSTERY_DEAL`.

These are deliberate data-quality issues, not accounting inconsistencies or broken foreign keys. The seeded row contents are deterministic for NumPy seed `20261025`.