create table report.PartnerSortingCenters_quality engine MergeTree order by dt_date as
select dt_date
     , uniq(wh_id) as wh_ids
     , uniq(office_id) as office_id
     , countIf(qty_export, qty_export < 1) as export_0
     , countIf(qty_arrived, qty_arrived < 1) as arrived_0
     , countIf(qty_sort, qty_sort < 1) as sort_0
     , countIf(qty_third_party_shipment, qty_third_party_shipment < 1) as third_party_shipment_0
     , countIf(received_shks_qty , received_shks_qty  < 1) as received_shks_0
from report.PartnerSortingCenters
group by dt_date
order by dt_date descending
