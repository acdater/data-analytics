from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection
from sqlalchemy.engine import URL

SEED = 20261025
CUSTOMER_COUNT = 5_000
PRODUCT_COUNT = 300
ORDER_COUNT = 25_000
BATCH_SIZE = 1_000

CATEGORY_NAMES = [
    "Electronics",
    "Home & Kitchen",
    "Apparel",
    "Beauty",
    "Sports & Outdoors",
    "Books",
    "Toys",
    "Office",
    "Pet Supplies",
    "Grocery",
]
FIRST_NAMES = ["Avery", "Jordan", "Morgan", "Riley", "Taylor", "Casey", "Quinn", "Jamie", "Cameron", "Reese"]
LAST_NAMES = ["Parker", "Reed", "Brooks", "Hayes", "Foster", "Bennett", "Coleman", "Price", "Ward", "Flores"]
CITIES = ["Austin", "Boston", "Chicago", "Denver", "Miami", "Portland", "Raleigh", "Seattle", "Tampa", "Phoenix"]
STATE_CODES = ["TX", "MA", "IL", "CO", "FL", "OR", "NC", "WA", "FL", "AZ"]
PRODUCT_ADJECTIVES = ["Everyday", "Essential", "Studio", "Summit", "Coastal", "Modern", "Heritage", "Core", "Select", "Flex"]
PRODUCT_NOUNS = ["Headphones", "Bottle", "Backpack", "Lamp", "Towel Set", "Jacket", "Cookware", "Speaker", "Desk Organizer", "Travel Mug"]


def money(value: Decimal | float | int) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def database_engine():
    required = ["POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"]
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise SystemExit(f"Missing environment variables: {', '.join(missing)}. Copy .env.example to .env.")

    url = URL.create(
        "postgresql+psycopg",
        username=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.getenv("POSTGRES_PORT", "5433")),
        database=os.environ["POSTGRES_DB"],
    )
    return create_engine(url, pool_pre_ping=True)


def insert_rows(connection: Connection, statement: str, rows: list[dict]) -> None:
    for offset in range(0, len(rows), BATCH_SIZE):
        connection.execute(text(statement), rows[offset : offset + BATCH_SIZE])


def build_dataset() -> dict[str, list[dict]]:
    rng = np.random.default_rng(SEED)
    categories = [
        {"category_id": category_id, "category_name": name, "description": f"Northstar {name.lower()} assortment"}
        for category_id, name in enumerate(CATEGORY_NAMES, start=1)
    ]

    customers = []
    for customer_id in range(1, CUSTOMER_COUNT + 1):
        first_name = FIRST_NAMES[(customer_id - 1) % len(FIRST_NAMES)]
        last_name = LAST_NAMES[((customer_id - 1) // len(FIRST_NAMES)) % len(LAST_NAMES)]
        email = f"customer{customer_id:05d}@example.test"
        if customer_id == 17:
            email = "customer17(at)example.test"
        elif customer_id == 821:
            email = "customer821.example.test"
        elif customer_id == 2701:
            email = " Customer2701@example.test "

        city_index = int(rng.integers(0, len(CITIES)))
        city = "" if customer_id in {1042, 3490} else CITIES[city_index]
        signup_day = date(2018, 1, 1) + timedelta(days=int(rng.integers(0, 2190)))
        customers.append(
            {
                "customer_id": customer_id,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "signup_date": signup_day,
                "city": city,
                "state_code": STATE_CODES[city_index],
                "phone": None if rng.random() < 0.22 else f"+1-555-{int(rng.integers(100, 1000)):03d}-{int(rng.integers(1000, 10000)):04d}",
                "loyalty_tier": str(rng.choice(["standard", "plus", "vip"], p=[0.72, 0.22, 0.06])),
            }
        )

    products = []
    product_by_id = {}
    for product_id in range(1, PRODUCT_COUNT + 1):
        category_id = ((product_id - 1) % len(CATEGORY_NAMES)) + 1
        list_price = money(np.clip(rng.lognormal(mean=3.55, sigma=0.62), 8, 450))
        unit_cost = money(list_price * Decimal(str(rng.uniform(0.57, 0.77))))
        product = {
            "product_id": product_id,
            "category_id": category_id,
            "sku": f"NS-{category_id:02d}-{product_id:04d}",
            "product_name": f"{PRODUCT_ADJECTIVES[(product_id - 1) % len(PRODUCT_ADJECTIVES)]} {PRODUCT_NOUNS[(product_id * 3) % len(PRODUCT_NOUNS)]} {product_id:03d}",
            "list_price": list_price,
            "unit_cost": unit_cost,
            "is_active": bool(rng.random() > 0.025),
        }
        products.append(product)
        product_by_id[product_id] = product

    days = pd.date_range("2024-01-01", "2026-01-01", inclusive="left", freq="D")
    month_weights = np.array([0.88, 0.82, 0.94, 0.91, 0.96, 0.92, 0.98, 1.00, 1.02, 1.12, 1.42, 1.62])
    day_weights = month_weights[days.month - 1] * np.linspace(1.0, 1.18, len(days))
    day_weights /= day_weights.sum()
    sampled_day_indexes = rng.choice(len(days), size=ORDER_COUNT, p=day_weights)
    sampled_seconds = rng.integers(0, 86_400, size=ORDER_COUNT)
    customer_weights = rng.pareto(1.65, size=CUSTOMER_COUNT) + 1.0
    customer_weights /= customer_weights.sum()
    order_statuses = ["pending", "paid", "shipped", "delivered", "cancelled"]
    order_status_probabilities = [0.01, 0.16, 0.16, 0.63, 0.04]

    orders = []
    order_items = []
    payments = []
    returns = []
    payment_id = 0
    order_item_id = 0
    return_id = 0
    product_ids = np.arange(1, PRODUCT_COUNT + 1)

    for order_id in range(1, ORDER_COUNT + 1):
        order_day = days[int(sampled_day_indexes[order_id - 1])]
        order_ts = pd.Timestamp(order_day).to_pydatetime().replace(tzinfo=timezone.utc)
        order_ts += timedelta(seconds=int(sampled_seconds[order_id - 1]))
        order_year = order_ts.year
        status = str(rng.choice(order_statuses, p=order_status_probabilities))
        item_count = int(rng.choice([1, 2, 3, 4, 5], p=[0.14, 0.34, 0.32, 0.15, 0.05]))
        selected_products = rng.choice(product_ids, size=item_count, replace=False)
        current_price_factor = Decimal("0.965") if order_year == 2024 else Decimal("1.00")
        historical_cost_factor = Decimal("0.92") if order_year == 2024 else Decimal("1.00")
        item_rows = []

        for product_id_value in selected_products:
            product_id = int(product_id_value)
            product = product_by_id[product_id]
            quantity = int(rng.choice([1, 2, 3], p=[0.83, 0.14, 0.03]))
            price_variation = Decimal(str(rng.uniform(0.97, 1.03)))
            cost_variation = Decimal(str(rng.uniform(0.99, 1.01)))
            unit_price = money(product["list_price"] * current_price_factor * price_variation)
            unit_cost = money(product["unit_cost"] * historical_cost_factor * cost_variation)
            line_subtotal = money(unit_price * quantity)
            discount_chance = 0.29 if order_year == 2024 else 0.38
            discount_rate = Decimal("0")
            discount_code = None
            if rng.random() < discount_chance:
                discount_rate = Decimal(str(rng.choice([0.05, 0.10, 0.15, 0.20, 0.25], p=[0.15, 0.36, 0.28, 0.16, 0.05])))
                discount_code = str(rng.choice(["WELCOME10", "SEASONAL15", "CLEARANCE"], p=[0.35, 0.45, 0.20]))
            if rng.random() < 0.001:
                discount_code = "MYSTERY_DEAL"
            line_discount = min(line_subtotal, money(line_subtotal * discount_rate))
            order_item_id += 1
            item_row = {
                "order_item_id": order_item_id,
                "order_id": order_id,
                "product_id": product_id,
                "quantity": quantity,
                "unit_price": unit_price,
                "unit_cost": unit_cost,
                "line_subtotal": line_subtotal,
                "discount_amount": line_discount,
                "discount_code": discount_code,
            }
            order_items.append(item_row)
            item_rows.append(item_row)

        subtotal = money(sum((item["line_subtotal"] for item in item_rows), Decimal("0")))
        discount_amount = money(sum((item["discount_amount"] for item in item_rows), Decimal("0")))
        taxable_subtotal = subtotal - discount_amount
        tax_amount = money(taxable_subtotal * Decimal("0.08"))
        shipping_fee = Decimal("0.00") if taxable_subtotal >= Decimal("75.00") else Decimal("6.95")
        total_amount = money(taxable_subtotal + tax_amount + shipping_fee)
        customer_id = int(rng.choice(np.arange(1, CUSTOMER_COUNT + 1), p=customer_weights))
        order_row = {
            "order_id": order_id,
            "customer_id": customer_id,
            "order_ts": order_ts,
            "order_status": status,
            "subtotal": subtotal,
            "discount_amount": discount_amount,
            "tax_amount": tax_amount,
            "shipping_fee": shipping_fee,
            "total_amount": total_amount,
        }
        orders.append(order_row)
        payment_id += 1
        if status == "cancelled":
            payment_type, payment_status, payment_amount = "void", "voided", Decimal("0.00")
        elif status == "pending":
            payment_type, payment_status, payment_amount = "charge", "pending", total_amount
        else:
            payment_type, payment_status, payment_amount = "charge", "captured", total_amount
        payments.append(
            {
                "payment_id": payment_id,
                "order_id": order_id,
                "payment_type": payment_type,
                "payment_status": payment_status,
                "amount": payment_amount,
                "payment_ts": order_ts + timedelta(minutes=2),
                "transaction_ref": f"NS-PAY-{payment_id:07d}",
            }
        )

        if status == "delivered" and rng.random() < 0.07:
            returned_item = item_rows[int(rng.integers(0, len(item_rows)))]
            return_quantity = int(rng.integers(1, returned_item["quantity"] + 1))
            return_date = (order_ts + timedelta(days=int(rng.integers(2, 46)))).date()
            returned_net = money(
                (returned_item["line_subtotal"] - returned_item["discount_amount"])
                * Decimal(return_quantity)
                / Decimal(returned_item["quantity"])
            )
            refund_tax = money(tax_amount * returned_net / taxable_subtotal) if taxable_subtotal else Decimal("0.00")
            refund_amount = money(returned_net + refund_tax)
            payment_id += 1
            return_id += 1
            payments.append(
                {
                    "payment_id": payment_id,
                    "order_id": order_id,
                    "payment_type": "refund",
                    "payment_status": "refunded",
                    "amount": refund_amount,
                    "payment_ts": datetime.combine(return_date, datetime.min.time(), tzinfo=timezone.utc),
                    "transaction_ref": f"NS-PAY-{payment_id:07d}",
                }
            )
            returns.append(
                {
                    "return_id": return_id,
                    "order_item_id": returned_item["order_item_id"],
                    "refund_payment_id": payment_id,
                    "return_date": return_date,
                    "quantity": return_quantity,
                    "refund_amount": refund_amount,
                    "return_status": "refunded",
                }
            )

    marketing_spend = []
    sources = ["Paid Search", "Paid Social", "Affiliate", "Email", "Display"]
    month_starts = pd.date_range("2024-01-01", "2026-01-01", inclusive="left", freq="MS")
    spend_bases = {"Paid Search": 18_000, "Paid Social": 14_000, "Affiliate": 6_500, "Email": 4_000, "Display": 8_000}
    marketing_spend_id = 0
    for month_index, spend_month_value in enumerate(month_starts):
        spend_month = spend_month_value.date()
        seasonal_factor = 1.35 if spend_month.month in {11, 12} else 1.0
        growth_factor = 1 + 0.12 * month_index / (len(month_starts) - 1)
        for source in sources:
            marketing_spend_id += 1
            spend = money(spend_bases[source] * seasonal_factor * growth_factor * rng.uniform(0.82, 1.18))
            impressions = int(spend * Decimal(str(rng.uniform(18, 42))))
            clicks = int(impressions * rng.uniform(0.012, 0.055))
            attributed_source = "Unattributed" if marketing_spend_id == 17 else source
            marketing_spend.append(
                {
                    "marketing_spend_id": marketing_spend_id,
                    "spend_month": spend_month,
                    "source": attributed_source,
                    "campaign_name": f"{source} | {spend_month:%Y-%m}",
                    "spend_amount": spend,
                    "impressions": impressions,
                    "clicks": clicks,
                }
            )

    return {
        "categories": categories,
        "customers": customers,
        "products": products,
        "orders": orders,
        "order_items": order_items,
        "payments": payments,
        "returns": returns,
        "marketing_spend": marketing_spend,
    }


INSERT_STATEMENTS = {
    "categories": "INSERT INTO categories (category_id, category_name, description) VALUES (:category_id, :category_name, :description)",
    "customers": "INSERT INTO customers (customer_id, email, first_name, last_name, signup_date, city, state_code, phone, loyalty_tier) VALUES (:customer_id, :email, :first_name, :last_name, :signup_date, :city, :state_code, :phone, :loyalty_tier)",
    "products": "INSERT INTO products (product_id, category_id, sku, product_name, list_price, unit_cost, is_active) VALUES (:product_id, :category_id, :sku, :product_name, :list_price, :unit_cost, :is_active)",
    "orders": "INSERT INTO orders (order_id, customer_id, order_ts, order_status, subtotal, discount_amount, tax_amount, shipping_fee, total_amount) VALUES (:order_id, :customer_id, :order_ts, :order_status, :subtotal, :discount_amount, :tax_amount, :shipping_fee, :total_amount)",
    "order_items": "INSERT INTO order_items (order_item_id, order_id, product_id, quantity, unit_price, unit_cost, line_subtotal, discount_amount, discount_code) VALUES (:order_item_id, :order_id, :product_id, :quantity, :unit_price, :unit_cost, :line_subtotal, :discount_amount, :discount_code)",
    "payments": "INSERT INTO payments (payment_id, order_id, payment_type, payment_status, amount, payment_ts, transaction_ref) VALUES (:payment_id, :order_id, :payment_type, :payment_status, :amount, :payment_ts, :transaction_ref)",
    "returns": "INSERT INTO returns (return_id, order_item_id, refund_payment_id, return_date, quantity, refund_amount, return_status) VALUES (:return_id, :order_item_id, :refund_payment_id, :return_date, :quantity, :refund_amount, :return_status)",
    "marketing_spend": "INSERT INTO marketing_spend (marketing_spend_id, spend_month, source, campaign_name, spend_amount, impressions, clicks) VALUES (:marketing_spend_id, :spend_month, :source, :campaign_name, :spend_amount, :impressions, :clicks)",
}


def main() -> None:
    dataset = build_dataset()
    engine = database_engine()
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE returns, payments, order_items, orders, marketing_spend, products, customers, categories RESTART IDENTITY CASCADE"))
        for table_name in ["categories", "customers", "products", "orders", "order_items", "payments", "returns", "marketing_spend"]:
            insert_rows(connection, INSERT_STATEMENTS[table_name], dataset[table_name])
    engine.dispose()
    print(f"Seeded reproducible Northstar Retail data (seed={SEED}).")
    for table_name, rows in dataset.items():
        print(f"{table_name}: {len(rows):,}")


if __name__ == "__main__":
    main()