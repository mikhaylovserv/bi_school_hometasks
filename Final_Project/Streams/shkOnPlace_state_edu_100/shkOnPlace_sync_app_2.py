from pyspark.sql import *
from pyspark.sql.functions import *
from pyspark.sql.types import *
from clickhouse_driver import Client
import datetime
import os
import pandas as pd
import json
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)

# Нужно указать, чтобы spark подгрузил lib для kafka.
os.environ['PYSPARK_SUBMIT_ARGS'] = '--jars org.apache.spark:spark-sql-kafka-0-10_2.12-3.5.0 --packages org.apache.spark:spark-sql-kafka-0-10_2.12-3.5.0 pyspark-shell'

# Загружаем конекты. Не выкладываем в гит файл с конектами.
with open('/opt/spark/Streams/credentials.json') as json_file:
#with open('/Users/sergeymikhaylov/Desktop/WB/School/bi_school_hometasks/Final_Project/test/test_creds.json') as json_file:
    сonnect_settings = json.load(json_file)

ch_db_name = "stage"
ch_dst_table = "ShkOnPlaceState_log"

ch_meta_db_name = "meta"
ch_meta_table = "shkonplace_offset"

client = Client(сonnect_settings['ch_local'][0]['host'],
                user=сonnect_settings['ch_local'][0]['user'],
                password=сonnect_settings['ch_local'][0]['password'],
                verify=False,
                database=ch_db_name,
                settings={"numpy_columns": True, 'use_numpy': True},
                compression=True)

# Разные переменные, задаются в params.json
spark_app_name = "shkOnPlace_edu_simple"
spark_ui_port = "8081"

kafka_host = сonnect_settings['kafka'][0]['host']
kafka_port = сonnect_settings['kafka'][0]['port']
kafka_topic = "final_project_topic"
kafka_batch_size = 50
processing_time = "5 second"

checkpoint_path = f'/opt/kafka_checkpoint_dir/{spark_app_name}/{kafka_topic}/v1'

# Создание сессии спарк.
spark = SparkSession \
    .builder \
    .appName(spark_app_name) \
    .config('spark.ui.port', spark_ui_port)\
    .config("spark.dynamicAllocation.enabled", "false") \
    .config("spark.executor.cores", "1") \
    .config("spark.task.cpus", "1") \
    .config("spark.num.executors", "1") \
    .config("spark.executor.instances", "1") \
    .config("spark.default.parallelism", "1") \
    .config("spark.cores.max", "1") \
    .config('spark.ui.port', spark_ui_port)\
    .getOrCreate()

# убираем разные Warning.
spark.sparkContext.setLogLevel("WARN")
spark.conf.set("spark.sql.adaptive.enabled", "false")
spark.conf.set("spark.sql.debug.maxToStringFields", 500)

# Описание как создается процесс spark structured streaming.
df = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", f"{kafka_host}:{kafka_port}") \
    .option("subscribe", kafka_topic) \
    .option("maxOffsetsPerTrigger", kafka_batch_size) \
    .option("startingOffsets", "earliest") \
    .option("failOnDataLoss", "false") \
    .option("forceDeleteTempCheckpointLocation", "true") \
    .load()


# .option("kafka.sasl.jaas.config", f'org.apache.kafka.common.security.plain.PlainLoginModule required username="{kafka_user}" password="{kafka_password}";') \
# .option("kafka.sasl.mechanism", "PLAIN") \
# .option("kafka.security.protocol", "SASL_PLAINTEXT") \

# Колонки, которые писать в ClickHouse. В kafka много колонок, не все могут быть нужны. Этот tuple нужен перед записью в ClickHouse.
columns_to_ch = ("shk_id", "dt", "is_deleted", "state_id", "wh_id")

# Схема сообщений в топике kafka. Используется при формировании batch.
schema = StructType([
    StructField("offset", LongType(), False),
    StructField("shk_id", LongType(), False),
    StructField("dt", TimestampType(), False),
    StructField("is_deleted", IntegerType(), False),
    StructField("state_id", StringType(), True),
    StructField("wh_id", IntegerType(), False)
])

sql_tmp_create = """create table tmp.tmp_shkOnPlace_edu_1000
    (
        offset          UInt64,
        shk_id          UInt64,
        dt              DateTime(3),
        is_deleted      UInt16,
        state_id        String,
        wh_id           UInt32
    )
        engine = Memory
"""

sql_insert = f"""insert into {ch_db_name}.{ch_dst_table}
    select shk_id
    , dt
    , is_deleted
    , state_id
    , sop.wh_id
    , dct.wh_name
    , 'shkOnPlace_kafka' entry
    from tmp.tmp_shkOnPlace_edu_1000 sop
    left join default.dict_PSC_Warehouse dct on sop.wh_id = dct.wh_id
"""

sql_meta_table = f"""
create table if not exists {ch_meta_db_name}.{ch_meta_table}
    (
        offset UInt64,
        dt_onplace DateTime64,
        dt_load DateTime materialized now()
    ) 
engine MergeTree order by (offset, dt_onplace)
"""

sql_offset_1st_insert = f"""
    insert into {ch_meta_db_name}.{ch_meta_table}
    select argMax(offset, dt) as max_offset, max(dt) as max_dt from tmp.tmp_shkOnPlace_edu_1000
"""

sql_offset_insert = f"""
    insert into {ch_meta_db_name}.{ch_meta_table}
    select argMax(offset, dt) as max_offset, max(dt) as max_dt from tmp.tmp_shkOnPlace_edu_1000
"""

client.execute("drop table if exists tmp.tmp_shkOnPlace_edu_1000")

def should_write_offset():
    max_dt_load_result = client.execute(f"SELECT max(dt_load) FROM {ch_meta_db_name}.{ch_meta_table}")
    max_dt_load = max_dt_load_result[0][0]
    if max_dt_load is None or max_dt_load < datetime.now() - timedelta(minutes=1):
        return True
    return False

def column_filter(df):
    # # select только нужные колонки.
    col_tuple = []
    for col in columns_to_ch:
        col_tuple.append(f"value.{col}")
    col_tuple.extend(["offset"])
    return df.selectExpr(col_tuple)

def load_to_ch(df):
    # Преобразуем в dataframe pandas и записываем в ClickHouse.
    df_pd = df.toPandas()
    client.insert_dataframe('INSERT INTO tmp.tmp_shkOnPlace_edu_1000 VALUES', df_pd)

# Функция обработки batch. На вход получает dataframe-spark.
def foreach_batch_function(df2, epoch_id):

    df_rows = df2.count()
    # Если dataframe не пустой, тогда продолжаем.
    if df_rows > 0:
        print("ДАТАФРЕЙМ НЕ ПУСТОЙ 102")

        # print(df2.show(100))
        # df2.printSchema()

        # Убираем ненужные колонки.
        df2 = column_filter(df2)
        df2.show(5)

        client.execute(sql_tmp_create)
        print("СОЗДАЛИ ВРЕМЯНКУ, НАЧИНАЕМ ПОДГРУЖАТЬ")

        # Записываем dataframe в ch.
        load_to_ch(df2)
        print("ЗАПИСАЛИ ДФ В КХ")
        # Добавляем объем и записываем в конечную таблицу.
        client.execute(sql_insert)
        print("ЗАПИСАЛИ ДФ В STAGE")

        if should_write_offset():
            client.execute(sql_offset_insert)
            print("ЗАПИСАЛИ ДФ OFFSET")
        else:
            print("ЗАПИСЬ OFFSET НЕ ТРЕБОВАЛАСЬ")

        client.execute("drop table if exists tmp.tmp_shkOnPlace_edu_1000")
    else:
        print("ДАТАФРЕЙМ ПУСТОЙ")

query = df.select(from_json(col("value").cast("string"), schema).alias("value"), col("offset")) \
    .writeStream \
    .trigger(processingTime=processing_time) \
    .option("checkpointLocation", checkpoint_path) \
    .foreachBatch(foreach_batch_function) \
    .start()

query.awaitTermination()