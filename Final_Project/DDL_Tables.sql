--таблица для получения offset
CREATE TABLE IF NOT EXISTS meta.shkonplace_offset
(
    `offset` UInt64,
    `dt_onplace` DateTime64(3),
    `dt_load` DateTime MATERIALIZED now()
)
ENGINE = MergeTree
ORDER BY (offset, dt_onplace)
SETTINGS index_granularity = 8192;

--таблица для всех данных из Kafka
CREATE TABLE IF NOT EXISTS stage.ShkOnPlaceState_log
(
    `shk_id` Int64,
    `dt` DateTime64(6),
    `is_deleted` UInt8 DEFAULT 0,
    `state_id` LowCardinality(String),
    `wh_id` UInt16,
    `wh_name` String,
    `entry` LowCardinality(String),
    `dt_load` DateTime MATERIALIZED now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMMDD(dt)
ORDER BY (shk_id, dt)
TTL toStartOfDay(dt) + toIntervalDay(2)
SETTINGS index_granularity = 8192;

----таблица словарь для всех данных из Kafka
CREATE TABLE IF NOT EXISTS default.dict_PSC_Warehouse
(
    `wh_id` UInt64,
    `wh_name` String,
    `office_id` UInt64,
    `office_name` String,
    `organization_id` UInt32,
    `organization_name` String,
    `organization_inn` String,
    `supplier_id` UInt32,
    `currency_code` UInt64,
    `currency_str_code` String
)
ENGINE = ReplacingMergeTree
ORDER BY wh_id
SETTINGS index_granularity = 8192;
