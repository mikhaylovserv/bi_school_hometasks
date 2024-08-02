--Реализовать через буферную таблицу заполнение stg слоя

-- stage
create table stage.ShkOnPlaceState_log
(
    shk_id    Int64,
    state_id  LowCardinality(String),
    wh_id     Int64,
    dt        DateTime,
    dt_load   DateTime materialized now()
)
engine = MergeTree() order by shk_id
TTL toStartOfDay(dt_load) + toIntervalDay(14)
SETTINGS index_granularity = 8192;

-- buffer
create table if not exists direct_log.ShkOnPlaceState_log
(
    shk_id    Int64,
    state_id  LowCardinality(String),
    wh_id     Int64,
    dt        DateTime,
    dt_load   DateTime materialized now()
)
engine = Buffer('stage', 'ShkOnPlaceState_log', 100, 10, 100, 10000, 100000, 10000000, 100000000);

--загружаем данные в буфер (файл shkonplace_from_pegas)
--выбираем данные из таблицы stage (файл shkonplace_from_localhost_stg)
select *, dt_load
from stage.ShkOnPlaceState_log;
