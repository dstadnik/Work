CREATE TABLE datamarts.delivery_magnit_d1_agg_shard on cluster c9qiio6jvghjs6arichp
(
    event_date Date,
    magnit_id String,
    appmetrica_device_id_arr Array(UInt64),
    service_name LowCardinality(String),
    delivery_type LowCardinality(String),
    os_name LowCardinality(String),
    city String,
    app_version_name String,
    appsflyer_id String,
    ab_arr Array(String),
    loyalty_card_id_arr Array(String),
    money_paid Decimal64(3),
    margin_paid Decimal64(3),
    order_arr Array(String),
    product_arr Array(String),
    app_launch_flg UInt8,
    catalog_main_flg UInt8,
    catalog_listing_flg UInt8,
    search_main_flg UInt8,
    search_result_flg UInt8,
    product_screen_flg UInt8,
    product_screen_to_cart_flg UInt8,
    listing_to_cart_flg UInt8,
    listing_to_item_flg UInt8,
    search_screen_to_cart_flg UInt8,
    cart_visit_flg UInt8,
    cart_2_checkout_flg UInt8,
    checkout_visit_flg UInt8,
    pay_button_pushed_flg UInt8,
    purchase_flg UInt8,
    order_id_app_arr Array(String),
    reg_dt Date,
    active_days_arr Array(Date),
    order_days_arr Array(Date),
    first_order_id_arr Array(String),
    first_order_dt Date
)
ENGINE = MergeTree
PARTITION BY event_date
ORDER BY (service_name, delivery_type, event_date, magnit_id)
SETTINGS index_granularity = 8192



CREATE TABLE datamarts.delivery_magnit_d1_agg on cluster c9qiio6jvghjs6arichp
(
    event_date Date,
    magnit_id String,
    appmetrica_device_id_arr Array(UInt64),
    service_name LowCardinality(String),
    delivery_type LowCardinality(String),
    os_name LowCardinality(String),
    city String,
    app_version_name String,
    appsflyer_id String,
    ab_arr Array(String),
    loyalty_card_id_arr Array(String),
    money_paid Decimal64(3),
    margin_paid Decimal64(3),
    order_arr Array(String),
    product_arr Array(String),
    app_launch_flg UInt8,
    catalog_main_flg UInt8,
    catalog_listing_flg UInt8,
    search_main_flg UInt8,
    search_result_flg UInt8,
    product_screen_flg UInt8,
    product_screen_to_cart_flg UInt8,
    listing_to_cart_flg UInt8,
    listing_to_item_flg UInt8,
    search_screen_to_cart_flg UInt8,
    cart_visit_flg UInt8,
    cart_2_checkout_flg UInt8,
    checkout_visit_flg UInt8,
    pay_button_pushed_flg UInt8,
    purchase_flg UInt8,
    order_id_app_arr Array(String),
    reg_dt Date,
    active_days_arr Array(Date),
    order_days_arr Array(Date),
    first_order_id_arr Array(String),
    first_order_dt Date
)

ENGINE = Distributed('c9qiio6jvghjs6arichp', 'datamarts', 'delivery_magnit_d1_agg_shard',cityHash64(event_date))
