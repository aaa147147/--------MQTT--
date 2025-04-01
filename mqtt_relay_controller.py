import json
import logging
import time

from paho.mqtt import client as mqtt_client


class MQTTClient:
    def __init__(self, broker, port, pub_topic, sub_topic, client_id, username, password, logger):
        self.broker = broker
        self.port = port
        self.pub_topic = pub_topic
        self.sub_topic = sub_topic
        self.client_id = client_id
        self.username = username
        self.password = password
        self.logger = logger

        self.client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION1, self.client_id)
        self.client.username_pw_set(self.username, self.password)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

        self.flag_exit = False
        self.first_reconnect_delay = 1
        self.reconnect_rate = 2
        self.max_reconnect_count = 12
        self.max_reconnect_delay = 60

        self.confirmation_received = False
        self.relay_state = 0

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0 and client.is_connected():
            self.logger.info("已成功连接到MQTT代理！")
            client.subscribe(self.sub_topic)
        else:
            self.logger.error(f'连接失败，返回码 {rc}')

    def on_disconnect(self, client, userdata, rc):
        self.logger.info(f"断开连接，返回码: {rc}")
        reconnect_count, reconnect_delay = 0, self.first_reconnect_delay
        while reconnect_count < self.max_reconnect_count:
            self.logger.info(f"将在 {reconnect_delay} 秒后重连...")
            time.sleep(reconnect_delay)

            try:
                client.reconnect()
                self.logger.info("重连成功！")
                return
            except Exception as err:
                self.logger.error(f"{err}。重连失败。正在重试...")

            reconnect_delay *= self.reconnect_rate
            reconnect_delay = min(reconnect_delay, self.max_reconnect_delay)
            reconnect_count += 1
        self.logger.info(f"经过 {reconnect_count} 次尝试后重连失败。正在退出...")
        self.flag_exit = True

    def on_message(self, client, userdata, msg):
        payload = json.loads(msg.payload.decode())
        self.logger.info(f"收到消息: {payload}")
        if payload.get("type") == "Socket-mini-v2" and int(payload.get("key")) == self.relay_state:
            self.confirmation_received = True

    def connect(self):
        self.client.connect(self.broker, self.port, keepalive=120)

    def subscribe(self, topic):
        if self.client.is_connected():
            self.client.subscribe(topic)
        else:
            self.logger.error("订阅：MQTT客户端未连接！")

    def publish(self, topic, message):
        msg = json.dumps(message)
        if not self.client.is_connected():
            self.logger.error("发布：MQTT客户端未连接！")
            return
        result = self.client.publish(topic, msg)
        status = result[0]
        if status == 0:
            self.logger.info(f'已发送 `{msg}` 到主题 `{topic}`')
        else:
            self.logger.error(f'发送消息到主题 {topic} 失败')

    def loop_start(self):
        self.client.loop_start()

    def loop_stop(self):
        self.client.loop_stop()

    def close(self):
        self.flag_exit = True
        self.client.disconnect()
        self.client.loop_stop()


class RelayController(MQTTClient):
    def __init__(self, broker, port, pub_topic, sub_topic, client_id, username, password, logger):
        super().__init__(broker, port, pub_topic, sub_topic, client_id, username, password, logger)

    def wait_for_confirmation(self, timeout=5):
        start_time = time.time()
        while not self.confirmation_received:
            if time.time() - start_time > timeout:
                raise Exception("在超时时间内未收到确认")
            time.sleep(0.1)

    def turn_on_relay(self):
        max_retries = 5
        self.relay_state = 1
        for attempt in range(max_retries):
            self.confirmation_received = False
            self.publish(self.pub_topic, {"type": "event", "key": 1})
            try:
                self.wait_for_confirmation()
                self.logger.info("继电器已成功打开")
                return
            except Exception as e:
                self.logger.error(f"尝试 {attempt + 1} 失败: {e}")
        raise Exception("多次尝试后继电器打开失败")

    def turn_off_relay(self):
        max_retries = 5
        self.relay_state = 0
        for attempt in range(max_retries):
            self.confirmation_received = False
            self.publish(self.pub_topic, {"type": "event", "key": 0})
            try:
                self.wait_for_confirmation()
                self.logger.info("继电器已成功关闭")
                return
            except Exception as e:
                self.logger.error(f"尝试 {attempt + 1} 失败: {e}")
        raise Exception("多次尝试后继电器关闭失败")


if __name__ == '__main__':
    logger = logging.getLogger('RelayController')
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    relay_controller = RelayController(
        broker='127.0.0.1',
        port=1883,
        pub_topic="test",
        sub_topic="test",
        client_id='yHRHObdxdHyB',
        username='MQTT1',
        password='123456',
        logger=logger
    )
    relay_controller.connect()
    relay_controller.loop_start()
    time.sleep(1)

    while True:
        if relay_controller.client.is_connected():
            relay_controller.turn_on_relay()
            time.sleep(5)  # 保持继电器打开5秒
            relay_controller.turn_off_relay()
            time.sleep(5)  # 保持继电器关闭5秒
        else:
            relay_controller.loop_stop()
    relay_controller.close()