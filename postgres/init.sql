CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    order_id INT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO transactions (order_id, quantity, unit_price) VALUES
(979, 3, 396000),
(691, 2, 258000),
(587, 4, 308000),
(580, 2, 196000),
(325, 2, 746000);
