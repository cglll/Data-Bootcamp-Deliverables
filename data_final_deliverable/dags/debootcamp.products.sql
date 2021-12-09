-- Table: debootcamp.products

CREATE SCHEMA IF NOT EXISTS debootcamp;

CREATE TABLE IF NOT EXISTS debootcamp.products
(
    InvoiceNo VARCHAR(10),
    StockCode VARCHAR(20),
    Description VARCHAR(1000),
    Quantity BIGINT,
    InvoiceDate TIMESTAMP,
    UnitPrice NUMERIC(8, 3),
    CustomerID BIGINT,
    Country VARCHAR(255)
);
