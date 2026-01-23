import time
import configparser
from types import SimpleNamespace
from event_manager import EventType

def load_config(logger, config_file='config.ini'):
    config = configparser.ConfigParser()
    if not config.read(config_file, encoding='utf-8'):
        logger.error(f"配置文件 {config_file} 未找到")
        while True:
            time.sleep(100)

    def get_config(section, option, default=None, required=False):
        try:
            value = config.get(section, option)
            if isinstance(value, str) and value.lower() in ['true', 'false']:
                value = value.lower() == 'true'
            logger.info(f"读取到配置项 {section}.{option}: {value}")
            return value
        except (configparser.NoSectionError, configparser.NoOptionError):
            if required:
                logger.error(f"配置项 {section}.{option} 未找到")
                while True:
                    time.sleep(100)
            logger.warning(f"配置项 {section}.{option} 未找到，使用默认值: {default}")
            return default

    IP_ADDRESSES = [x.strip() for x in get_config('Settings', 'IP_ADDRESSES', required=True).split(',') if x.strip()]
    TIMEDELAY = int(get_config('Settings', 'TIMEDELAY', default=5, required=True))
    TIMEOUT = int(get_config('Settings', 'TIMEOUT', default=240, required=True))
    TIME_RELAYOFF = int(get_config('Settings', 'TIME_RELAYOFF', default=10, required=True))
    ADBDEVICECKR_ENABLED = bool(get_config('Settings', 'ADBDEVICECKR_ENABLED', default=False, required=True))
    THREADTEST_ENABLED = bool(get_config('Settings', 'THREADTEST_ENABLED', default=False, required=True))
    CYCLEPINGTEST_ENABLED = bool(get_config('Settings', 'CYCLEPINGTEST_ENABLED', default=False, required=True))
    MAX_PING_RTT = bool(get_config('Settings', 'MAX_PING_RTT', default=500, required=True))

    CYCLEPINGTEST_TIMES = int(get_config('CYCLEPINGTEST', 'CYCLEPINGTEST_TIMES', default=5, required=True))
    CYCLEPINGTEST_DELAY = int(get_config('CYCLEPINGTEST', 'CYCLEPINGTEST_DELAY', default=5, required=True))

    RELAY_BROKER = get_config('MQTT', 'RELAY_BROKER', required=True)
    RELAY_PORT = int(get_config('MQTT', 'RELAY_PORT', default=1883, required=True))
    RELAY_PUB_TOPIC = get_config('MQTT', 'RELAY_PUB_TOPIC', required=True)
    RELAY_SUB_TOPIC = get_config('MQTT', 'RELAY_SUB_TOPIC', required=True)
    RELAY_CLIENT_ID = get_config('MQTT', 'RELAY_CLIENT_ID', required=True)
    RELAY_USERNAME = get_config('MQTT', 'RELAY_USERNAME', required=True)
    RELAY_PASSWORD = get_config('MQTT', 'RELAY_PASSWORD', required=True)
    RELAY_message_check_name = get_config('MQTT', 'message_check_name', required=True)
    RELAY_message_check_key = get_config('MQTT', 'message_check_key', required=True)
    RELAY_message_check_value = get_config('MQTT', 'message_check_value', required=True)

    DINGTALK_WEBHOOK_URL = get_config('DingTalk', 'DINGTALK_WEBHOOK_URL', required=True)
    DINGTALK_MESSAGE_TIMEOUT = get_config('DingTalk', 'DINGTALK_MESSAGE_TIMEOUT', required=True)
    DINGTALK_MESSAGE_ERROR = get_config('DingTalk', 'DINGTALK_MESSAGE_ERROR', required=True)

    EVENT_ACTIONS = {t.name: "exit" for t in EventType}
    try:
        for k, v in config.items('EventActions'):
            EVENT_ACTIONS[k.strip().upper()] = str(v).strip().lower()
            logger.info(f"读取到事件处理映射关系 {k.strip().upper()}: {EVENT_ACTIONS[k.strip().upper()]}")
    except (configparser.NoSectionError):
        logger.error("配置项 EventActions 未找到")
        while True:
            time.sleep(100)

    return SimpleNamespace(
        IP_ADDRESSES=IP_ADDRESSES,
        TIMEDELAY=TIMEDELAY,
        TIMEOUT=TIMEOUT,
        TIME_RELAYOFF=TIME_RELAYOFF,
        ADBDEVICECKR_ENABLED=ADBDEVICECKR_ENABLED,
        THREADTEST_ENABLED=THREADTEST_ENABLED,
        CYCLEPINGTEST_ENABLED=CYCLEPINGTEST_ENABLED,
        CYCLEPINGTEST_TIMES=CYCLEPINGTEST_TIMES,
        CYCLEPINGTEST_DELAY=CYCLEPINGTEST_DELAY,
        RELAY_BROKER=RELAY_BROKER,
        RELAY_PORT=RELAY_PORT,
        RELAY_PUB_TOPIC=RELAY_PUB_TOPIC,
        RELAY_SUB_TOPIC=RELAY_SUB_TOPIC,
        RELAY_CLIENT_ID=RELAY_CLIENT_ID,
        RELAY_USERNAME=RELAY_USERNAME,
        RELAY_PASSWORD=RELAY_PASSWORD,
        RELAY_message_check_name=RELAY_message_check_name,
        RELAY_message_check_key=RELAY_message_check_key,
        RELAY_message_check_value=RELAY_message_check_value,
        DINGTALK_WEBHOOK_URL=DINGTALK_WEBHOOK_URL,
        DINGTALK_MESSAGE_TIMEOUT=DINGTALK_MESSAGE_TIMEOUT,
        DINGTALK_MESSAGE_ERROR=DINGTALK_MESSAGE_ERROR,
        EVENT_ACTIONS=EVENT_ACTIONS,
        MAX_PING_RTT = MAX_PING_RTT
    )
