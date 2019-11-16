import os

mqtt = os.getenv('MQTT_SERVER_IP')
username = os.environ.get('MQTT_USER')
password = os.environ.get('MQTT_PW')

for value in [mqtt,username, password]:
    print(value)