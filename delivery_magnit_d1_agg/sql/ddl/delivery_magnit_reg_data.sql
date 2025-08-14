CREATE TABLE datamarts.delivery_magnit_reg_data_shard on cluster c9qiio6jvghjs6arichp
(
    magnit_id String,
    service_name LowCardinality(String),
    delivery_type LowCardinality(String),
    first_order_dt Date,
    first_order_id_arr Array(String)
)
ENGINE = MergeTree
PARTITION BY first_order_dt
ORDER BY (service_name, delivery_type, first_order_dt, magnit_id)
SETTINGS index_granularity = 8192



CREATE TABLE datamarts.delivery_magnit_reg_data on cluster c9qiio6jvghjs6arichp
(

    magnit_id String,
    service_name LowCardinality(String),
    delivery_type LowCardinality(String),
    first_order_dt Date,
    first_order_id_arr Array(String)
)

ENGINE = Distributed('c9qiio6jvghjs6arichp', 'datamarts', 'delivery_magnit_reg_data_shard',cityHash64(magnit_id))
