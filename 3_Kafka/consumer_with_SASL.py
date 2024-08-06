from confluent_kafka import Consumer, KafkaError

config = {
    'bootstrap.servers': 'localhost:9093', # указываем брокеров
    'group.id': 'my-group',  # Уникальный ID группы потребителей
    'auto.offset.reset': 'earliest',  # Начинать чтение с самого старого сообщения
    'sasl.mechanism':'PLAIN',
    'security.protocol':'SASL_PLAINTEXT',
    'sasl.username':'admin',
    'sasl.password':'admin-secret'
}

consumer = Consumer(**config)
consumer.subscribe(['hometask_topic'])



def read_messages():
    try:
        while True:
            msg = consumer.poll(timeout=1.0)  # Задержка в секундах для ожидания сообщения
            if msg is None:
                continue  # Нет сообщения в течение заданного времени
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    # Конец партиции, но это не ошибка
                    continue
                else:
                    print(f"Error: {msg.error()}")
                    break  # Ошибка при чтении сообщения
            print(f"Received message: {msg.value().decode('utf-8')}")
    finally:
        consumer.close()  # Закрытие потребителя при завершении работы

if __name__ == '__main__':
    read_messages()