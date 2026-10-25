from sqlalchemy import text

from northstar_retail_analytics.seed import database_engine

COUNT_QUERY = text(
    """
    SELECT
        (SELECT COUNT(*) FROM categories) AS categories,
        (SELECT COUNT(*) FROM customers) AS customers,
        (SELECT COUNT(*) FROM products) AS products,
        (SELECT COUNT(*) FROM orders) AS orders,
        (SELECT COUNT(*) FROM order_items) AS order_items,
        (SELECT COUNT(*) FROM payments) AS payments,
        (SELECT COUNT(*) FROM returns) AS returns,
        (SELECT COUNT(*) FROM marketing_spend) AS marketing_spend
    """
)

ORPHAN_QUERY = text(
    """
    SELECT COUNT(*) AS orphan_count
    FROM (
        SELECT o.order_id FROM orders o LEFT JOIN customers c USING (customer_id) WHERE c.customer_id IS NULL
        UNION ALL
        SELECT p.product_id FROM products p LEFT JOIN categories c USING (category_id) WHERE c.category_id IS NULL
        UNION ALL
        SELECT i.order_item_id FROM order_items i LEFT JOIN orders o USING (order_id) WHERE o.order_id IS NULL
        UNION ALL
        SELECT i.order_item_id FROM order_items i LEFT JOIN products p USING (product_id) WHERE p.product_id IS NULL
        UNION ALL
        SELECT p.payment_id FROM payments p LEFT JOIN orders o USING (order_id) WHERE o.order_id IS NULL
        UNION ALL
        SELECT r.return_id FROM returns r LEFT JOIN order_items i USING (order_item_id) WHERE i.order_item_id IS NULL
        UNION ALL
        SELECT r.return_id FROM returns r LEFT JOIN payments p ON p.payment_id = r.refund_payment_id WHERE p.payment_id IS NULL
    ) AS orphan_rows
    """
)

FINANCIAL_ISSUES_QUERY = text(
    """
    SELECT COUNT(*) AS issue_count
    FROM orders o
    LEFT JOIN (
        SELECT order_id, SUM(line_subtotal) AS item_subtotal, SUM(discount_amount) AS item_discount
        FROM order_items
        GROUP BY order_id
    ) i USING (order_id)
    WHERE o.subtotal <> COALESCE(i.item_subtotal, 0)
       OR o.discount_amount <> COALESCE(i.item_discount, 0)
       OR o.total_amount <> o.subtotal - o.discount_amount + o.tax_amount + o.shipping_fee
    """
)

REFUND_ISSUES_QUERY = text(
    """
    SELECT COUNT(*) AS issue_count
    FROM returns r
    JOIN payments p ON p.payment_id = r.refund_payment_id
    WHERE p.payment_type <> 'refund'
       OR p.payment_status <> 'refunded'
       OR p.amount <> r.refund_amount
    """
)

PAYMENT_ISSUES_QUERY = text(
    """
    SELECT COUNT(*) AS issue_count
    FROM (
        SELECT
            o.order_id,
            o.total_amount,
            o.order_status,
            COUNT(p.payment_id) FILTER (
                WHERE (o.order_status = 'cancelled' AND p.payment_type = 'void' AND p.payment_status = 'voided' AND p.amount = 0)
                   OR (o.order_status = 'pending' AND p.payment_type = 'charge' AND p.payment_status = 'pending' AND p.amount = o.total_amount)
                   OR (o.order_status NOT IN ('cancelled', 'pending') AND p.payment_type = 'charge' AND p.payment_status = 'captured' AND p.amount = o.total_amount)
            ) AS valid_primary_events,
            COALESCE(SUM(p.amount) FILTER (WHERE p.payment_type = 'refund'), 0) AS refund_total,
            COALESCE(SUM(p.amount) FILTER (WHERE p.payment_type = 'charge' AND p.payment_status = 'captured'), 0) AS captured_total
        FROM orders o
        LEFT JOIN payments p USING (order_id)
        GROUP BY o.order_id
    ) payment_checks
    WHERE valid_primary_events <> 1 OR refund_total > captured_total
    """
)

RETURN_QUANTITY_ISSUES_QUERY = text(
    """
    SELECT COUNT(*) AS issue_count
    FROM returns r
    JOIN order_items i USING (order_item_id)
    JOIN orders o USING (order_id)
    WHERE r.quantity > i.quantity OR o.order_status <> 'delivered'
    """
)


def main() -> None:
    engine = database_engine()
    with engine.connect() as connection:
        server = connection.execute(text("SELECT version() AS version")).scalar_one()
        counts = connection.execute(COUNT_QUERY).mappings().one()
        orphan_count = connection.execute(ORPHAN_QUERY).scalar_one()
        financial_issues = connection.execute(FINANCIAL_ISSUES_QUERY).scalar_one()
        refund_issues = connection.execute(REFUND_ISSUES_QUERY).scalar_one()
        payment_issues = connection.execute(PAYMENT_ISSUES_QUERY).scalar_one()
        return_quantity_issues = connection.execute(RETURN_QUANTITY_ISSUES_QUERY).scalar_one()

    print(f"Connected: {server.split(',')[0]}")
    for table_name, row_count in counts.items():
        print(f"{table_name}: {row_count:,}")

    expected = {"categories": 10, "customers": 5_000, "products": 300, "orders": 25_000, "marketing_spend": 120}
    failures = [f"{table}: expected {count}, got {counts[table]}" for table, count in expected.items() if counts[table] != count]
    if not 50_000 <= counts["order_items"] <= 80_000:
        failures.append(f"order_items: expected 50,000-80,000, got {counts['order_items']}")
    if counts["payments"] < counts["orders"] or counts["returns"] == 0:
        failures.append("payments or returns are unexpectedly empty")
    if orphan_count:
        failures.append(f"found {orphan_count} orphaned foreign-key references")
    if financial_issues:
        failures.append(f"found {financial_issues} order accounting inconsistencies")
    if refund_issues:
        failures.append(f"found {refund_issues} return/refund inconsistencies")
    if payment_issues:
        failures.append(f"found {payment_issues} payment amount or status inconsistencies")
    if return_quantity_issues:
        failures.append(f"found {return_quantity_issues} invalid return quantities or non-delivered returns")
    engine.dispose()

    if failures:
        raise SystemExit("Validation failed:\n- " + "\n- ".join(failures))
    print("Validation passed: expected scale, referential integrity, order totals, and refunds are consistent.")


if __name__ == "__main__":
    main()