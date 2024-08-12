from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import pandas as pd
from clickhouse_driver import Client
from sqlalchemy import create_engine

default_args = {
    'owner': 'Sergey',
    'start_date': datetime(2024, 8, 10)
}

dag = DAG(
    dag_id='report_hometask_airflow',
    default_args=default_args,
    schedule_interval='15 6 * * *',
    # description='',
    catchup=False,
    max_active_runs=1
)


def main():
    import json
    import psycopg2
    from clickhouse_driver import Client

    days_ago = 0

    with open('/opt/airflow/dags/keys/connect.json') as json_file:
        param_сonnect = json.load(json_file)

    client_CH = Client(
        param_сonnect['clickhouse'][0]['host'],
        user=param_сonnect['clickhouse'][0]['user'],
        password=param_сonnect['clickhouse'][0]['password'],
        port=param_сonnect['clickhouse'][0]['port'],
        verify=False,
        compression=True
    )

    client_PG = psycopg2.connect(
        host=param_сonnect['postgres'][0]['host'],
        user=param_сonnect['postgres'][0]['user'],
        password=param_сonnect['postgres'][0]['password'],
        port=param_сonnect['postgres'][0]['port'],
        database=param_сonnect['postgres'][0]['database']
    )


    client_CH.execute(f"""create table if not exists report.agg_export_onPSC (
                        wh_id Int64
                       , dt_date Date
                       , total_qty_export Int64
                       , dt_load materialized now()
                    ) engine ReplacingMergeTree order by (wh_id, dt_date)""")

    client_CH.execute(f"""insert into report.agg_export_onPSC
                        select wh_id
                             , dt_date
                             , sum(qty_export) as total_qty_export
                        from report.PartnerSortingCenters
                        where dt_date >= (select max(dt_date) from report.agg_export_onPSC)
                        group by wh_id, dt_date""")

    result = client_CH.query_dataframe("""select  wh_id, dt_date, total_qty_export
                                    from report.agg_export_onPSC
                                    where dt_load = (select max(dt_load) from report.agg_export_onPSC)
                                    """)

    print(result)



    # Преобразование результата в DataFrame
    df = pd.DataFrame(result, columns=["wh_id", "dt_date", "total_qty_export"])

    # Преобразование DataFrame в JSON
    json_data = df.to_json(orient='records', date_format='iso', date_unit='s')

    print(json_data)

    cursor = client_PG.cursor()
    cursor.execute(f"SELECT sync.hometask_function(_src := '{json_data}')")

    client_PG.commit()

    cursor.close()
    client_PG.close()
    client_CH.disconnect()

    print("URA!!!")



task_tarificator_by_prod_type_parts = PythonOperator(
    task_id='report_hometask_airflow', python_callable=main, dag=dag)


