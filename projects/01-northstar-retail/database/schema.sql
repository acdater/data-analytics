CREATE TABLE IF NOT EXISTS categories (
    category_id INTEGER PRIMARY KEY,
    category_name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    signup_date DATE NOT NULL,
    city TEXT NOT NULL,
    state_code CHAR(2) NOT NULL,
    phone TEXT,
    loyalty_tier TEXT NOT NULL CHECK (loyalty_tier IN ('standard', 'plus', 'vip'))
);

CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES categories(category_id),
    sku TEXT NOT NULL UNIQUE,
    product_name TEXT NOT NULL,
    list_price NUMERIC(10, 2) NOT NULL CHECK (list_price > 0),
    unit_cost NUMERIC(10, 2) NOT NULL CHECK (unit_cost > 0 AND unit_cost <= list_price),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    order_ts TIMESTAMPTZ NOT NULL,
    order_status TEXT NOT NULL CHECK (order_status IN ('pending', 'paid', 'shipped', 'delivered', 'cancelled')),
    subtotal NUMERIC(12, 2) NOT NULL CHECK (subtotal >= 0),
    discount_amount NUMERIC(12, 2) NOT NULL CHECK (discount_amount >= 0 AND discount_amount <= subtotal),
    tax_amount NUMERIC(12, 2) NOT NULL CHECK (tax_amount >= 0),
    shipping_fee NUMERIC(12, 2) NOT NULL CHECK (shipping_fee >= 0),
    total_amount NUMERIC(12, 2) NOT NULL CHECK (total_amount >= 0),
    CHECK (total_amount = subtotal - discount_amount + tax_amount + shipping_fee)
);

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    quantity SMALLINT NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(10, 2) NOT NULL CHECK (unit_price > 0),
    unit_cost NUMERIC(10, 2) NOT NULL CHECK (unit_cost > 0),
    line_subtotal NUMERIC(12, 2) NOT NULL CHECK (line_subtotal > 0),
    discount_amount NUMERIC(12, 2) NOT NULL CHECK (discount_amount >= 0 AND discount_amount <= line_subtotal),
    discount_code TEXT,
    CHECK (line_subtotal = quantity * unit_price)
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    payment_type TEXT NOT NULL CHECK (payment_type IN ('charge', 'refund', 'void')),
    payment_status TEXT NOT NULL CHECK (payment_status IN ('pending', 'captured', 'refunded', 'voided')),
    amount NUMERIC(12, 2) NOT NULL CHECK (amount >= 0),
    payment_ts TIMESTAMPTZ NOT NULL,
    transaction_ref TEXT NOT NULL UNIQUE,
    CHECK (payment_type <> 'void' OR amount = 0)
);

CREATE TABLE IF NOT EXISTS returns (
    return_id INTEGER PRIMARY KEY,
    order_item_id INTEGER NOT NULL REFERENCES order_items(order_item_id) ON DELETE CASCADE,
    refund_payment_id INTEGER NOT NULL UNIQUE REFERENCES payments(payment_id),
    return_date DATE NOT NULL,
    quantity SMALLINT NOT NULL CHECK (quantity > 0),
    refund_amount NUMERIC(12, 2) NOT NULL CHECK (refund_amount > 0),
    return_status TEXT NOT NULL CHECK (return_status IN ('approved', 'refunded', 'rejected'))
);

CREATE TABLE IF NOT EXISTS marketing_spend (
    marketing_spend_id INTEGER PRIMARY KEY,
    spend_month DATE NOT NULL,
    source TEXT NOT NULL,
    campaign_name TEXT NOT NULL,
    spend_amount NUMERIC(12, 2) NOT NULL CHECK (spend_amount >= 0),
    impressions BIGINT NOT NULL CHECK (impressions >= 0),
    clicks BIGINT NOT NULL CHECK (clicks >= 0 AND clicks <= impressions),
    UNIQUE (spend_month, source, campaign_name)
);

CREATE INDEX IF NOT EXISTS idx_customers_signup_date ON customers(signup_date);
CREATE INDEX IF NOT EXISTS idx_products_category_id ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_orders_customer_ts ON orders(customer_id, order_ts);
CREATE INDEX IF NOT EXISTS idx_orders_ts_status ON orders(order_ts, order_status);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_payments_order_id ON payments(order_id);
CREATE INDEX IF NOT EXISTS idx_payments_type_status ON payments(payment_type, payment_status);
CREATE INDEX IF NOT EXISTS idx_returns_order_item_id ON returns(order_item_id);
CREATE INDEX IF NOT EXISTS idx_marketing_spend_month ON marketing_spend(spend_month);