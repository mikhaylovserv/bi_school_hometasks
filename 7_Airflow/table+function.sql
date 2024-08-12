--таблица
create table "agg_export_onPSC"
(
    index            bigint,
    wh_id            bigint,
    dt_date          timestamp,
    total_qty_export bigint
);

alter table "agg_export_onPSC"
    owner to "default";

create index "ix_agg_export_onPSC_index"
    on "agg_export_onPSC" (index);

--функция
CREATE OR REPLACE FUNCTION sync.hometask_function(_src JSON) RETURNS JSON
    SECURITY DEFINER
    LANGUAGE plpgsql
AS
$$
BEGIN
    -- AD Получение МХ для ШК лоста
    INSERT INTO public."agg_export_onPSC" (wh_id, dt_date, total_qty_export)
    SELECT (j ->> 'wh_id')::int AS wh_id,
           (j ->> 'dt_date')::date  AS dt_date,
           (j ->> 'total_qty_export')::bigint    AS total_qty_export
    FROM JSON_ARRAY_ELEMENTS(_src) j
    ON CONFLICT DO NOTHING;

    RETURN JSON_BUILD_OBJECT('data', NULL);
END;
$$;
