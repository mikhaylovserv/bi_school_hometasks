-- выбираем данные, вставленные в схему stage и заполнившие current через мат вью
select *, dt_load
from current.ShkOnPlaceState_log;
--файл mat_view_ShkOnPlaceState_log.csv
