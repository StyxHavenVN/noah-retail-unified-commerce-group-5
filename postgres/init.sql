CREATE TABLE IF NOT EXISTS transactions (
    id          SERIAL PRIMARY KEY,
    order_id    INT UNIQUE NOT NULL,   -- UNIQUE bắt buộc để ON CONFLICT hoạt động
    user_id     INT NOT NULL,
    product_id  INT NOT NULL,
    quantity    INT NOT NULL,
    synced_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);