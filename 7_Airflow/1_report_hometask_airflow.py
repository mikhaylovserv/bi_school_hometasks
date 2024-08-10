from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
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
    client = Client('clickhouse-server'
                    , port=9000
                    , user='airflow'
                    , password='airflow123'
                    , verify=False
                    , database='default'
                    , settings={'numpy_columns': False, 'use_numpy': True}
                    , compression=False)


    client.execute(f"""create table if not exists report.agg_export_onPSC (
                        wh_id Int64
                       , dt_date Date
                       , total_qty_export Int64
                       , dt_load materialized now()
                    ) engine ReplacingMergeTree order by (wh_id, dt_date)""")

    client.execute(f"""insert into report.agg_export_onPSC
                        select wh_id
                             , dt_date
                             , sum(qty_export) as total_qty_export
                        from report.PartnerSortingCenters
                        where dt_date >= (select max(dt_date) from report.agg_export_onPSC)
                        group by wh_id, dt_date""")

    df = client.query_dataframe("""select  wh_id, dt_date, total_qty_export
                                    from report.agg_export_onPSC
                                    where dt_load = (select max(dt_load) from report.agg_export_onPSC)
                                    """)

    print(df)

    #Подключаемся к локальному постгресу
    engine = create_engine('postgresql://default:default@local-postgres:5432/postgres')
    #Вставляем данные в таблицу на постгресе
    df.to_sql('agg_export_onPSC', engine, if_exists="append")

    print("URA!!!")



task_report_hometask_airflow = PythonOperator(
    task_id='report_hometask_airflow', python_callable=main, dag=dag)


