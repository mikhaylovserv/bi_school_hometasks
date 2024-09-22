from clickhouse_driver import Client
import json
import time
from time import sleep
from dataclasses import dataclass
from datetime import datetime, timedelta
from confluent_kafka import Producer
import pandas as pd


config = {
    'bootstrap.servers': '192.168.1.136:29092',  # адрес Kafka сервера
    'client.id': 'simple-producer'
    # 'sasl.mechanism':'PLAIN',
    # 'security.protocol': 'SASL_PLAINTEXT',
    # 'sasl.username': 'admin',
    # 'sasl.password': 'admin-secret'
}

def connect_CH():
    with open(f"/Users/sergeymikhaylov/Desktop/WB/School/bi_school_hometasks/3_Kafka/3_kafka_hometask/ch_db.json") as json_file:
        param_connect = json.load(json_file)
        for _ in range(7):
            try:
                client = Client(param_connect['server'][0]['host'],
                                user=param_connect['server'][0]['user'],
                                password=param_connect['server'][0]['password'],
                                port=param_connect['server'][0]['port'],
                                verify=False,
                                database='',
                                settings={"numpy_columns": True, 'use_numpy': True},
                                compression=True)
                return client
            except Exception as e:
                print(e, "Нет коннекта к КликХаус")
                time.sleep(60)

producer = Producer(**config)

def delivery_report(err, msg):
    if err is not None:
        print(f"Message delivery failed: {err}")
    else:
        print(f"Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")

def send_message(data):
    try:
        # Асинхронная отправка сообщения
        producer.produce('final_project_topic', json.dumps(data).encode('utf-8'), callback=delivery_report)
        producer.poll(0)  # Поллинг для обработки обратных вызовов
    except BufferError:
        print(f"Local producer queue is full ({len(producer)} messages awaiting delivery): try again")

def main():
    client = connect_CH()
    result = client.execute("""
        select shk_id, dt, is_deleted, state_id, wh_id
        from default.ShkOnPlaceState_log
        where dt >= now() - interval 10 minute 
            and wh_id global in (select wh_id from dictionary.Warehouse where is_partner_sc = 1)
        order by dt descending
        limit 10000
    """)

    print(result)

    for row in result:

        data = {'shk_id': int(row[0])
                , 'dt' : (datetime(1970, 1, 1) + timedelta(microseconds=row[1] / 1000)).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                , 'is_deleted': int(row[2])
                ,'state_id': str(row[3])
                , 'wh_id': int(row[4])}

        send_message(data)
        producer.flush()

if __name__ == '__main__':
    main()
