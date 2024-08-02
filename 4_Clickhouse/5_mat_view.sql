--создаем таблицу для mat view
create table current.ShkOnPlaceState_log
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

--создаем mat view
create materialized view stage.v_stgShkOnP_to_currShkOnP to current.ShkOnPlaceState_log as
select shk_id, state_id, wh_id, dt
from stage.ShkOnPlaceState_log;

-- выбираем данные, вставленные в схему stage и заполнившие current через мат вью
select *, dt_load
from current.ShkOnPlaceState_log;
--файл mat_view_ShkOnPlaceState_log.csv
