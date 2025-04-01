import time
import logging
import subprocess
import requests
import configparser
import sys
import ctypes
import json
import datetime
import traceback

from mqtt_relay_controller import RelayController  # 引入RelayController类
from adbdeviceckr import DeviceMonitor
from cyclepingtest import Cyclepingtest

# 设置控制台窗口标题
ctypes.windll.kernel32.SetConsoleTitleW('PingTest-V02 Copyright © 2024 #EE_Lixin. All Rights Reserved.')

current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

LOG_FILE = f"./log/{current_time}-logfile.txt"
# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 创建文件处理器，并设置文件模式为 'w' 以覆盖文件
file_handler = logging.FileHandler(LOG_FILE, mode='w')
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(message)s')
file_handler.setFormatter(file_formatter)

# 创建控制台处理器
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_formatter = logging.Formatter('%(asctime)s - %(message)s')
stream_handler.setFormatter(stream_formatter)

# 添加处理器到日志记录器
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# 读取配置文件
config = configparser.ConfigParser()
config_file = 'config.ini'

if not config.read(config_file, encoding='utf-8'):
    logger.error(f"配置文件 {config_file} 未找到")
    while True:
        time.sleep(100)

# 检查并读取配置项
def get_config(section, option, default=None, required=False):
    try:
        value = config.get(section, option)
        if value.lower() in ['true', 'false']:
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

# 配置项
IP_ADDRESSES = get_config('Settings', 'IP_ADDRESSES', required=True).split(',')
TIMEDELAY = int(get_config('Settings', 'TIMEDELAY', default=5, required=True))
TIMEOUT = int(get_config('Settings', 'TIMEOUT', default=240, required=True))
TIME_RELAYOFF = int(get_config('Settings', 'TIME_RELAYOFF', default=10, required=True))
ADBDEVICECKR_ENABLED = get_config('Settings', 'ADBDEVICECKR_ENABLED', default=False, required=True)
THREADTEST_ENABLED = get_config('Settings', 'THREADTEST_ENABLED', default=False, required=True)
CYCLEPINGTEST_ENABLED = get_config('Settings', 'CYCLEPINGTEST_ENABLED', default=False, required=True)

CYCLEPINGTEST_TIMES = int(get_config('CYCLEPINGTEST', 'CYCLEPINGTEST_TIMES', default=5, required=True))
CYCLEPINGTEST_DELAY = int(get_config('CYCLEPINGTEST', 'CYCLEPINGTEST_DELAY', default=5, required=True))

RELAY_BROKER = get_config('MQTT', 'RELAY_BROKER', required=True)
RELAY_PORT = int(get_config('MQTT', 'RELAY_PORT', default=1883, required=True))
RELAY_PUB_TOPIC = get_config('MQTT', 'RELAY_PUB_TOPIC', required=True)
RELAY_SUB_TOPIC = get_config('MQTT', 'RELAY_SUB_TOPIC', required=True)
RELAY_CLIENT_ID = get_config('MQTT', 'RELAY_CLIENT_ID', required=True)
RELAY_USERNAME = get_config('MQTT', 'RELAY_USERNAME', required=True)
RELAY_PASSWORD = get_config('MQTT', 'RELAY_PASSWORD', required=True)

DINGTALK_WEBHOOK_URL = get_config('DingTalk', 'DINGTALK_WEBHOOK_URL', required=True)
DINGTALK_MESSAGE_TIMEOUT = get_config('DingTalk', 'DINGTALK_MESSAGE_TIMEOUT', required=True)
DINGTALK_MESSAGE_ERROR = get_config('DingTalk', 'DINGTALK_MESSAGE_ERROR', required=True)


# 配置继电器MQTT
relay_controller = RelayController(
    broker=RELAY_BROKER,
    port=RELAY_PORT,
    pub_topic=RELAY_PUB_TOPIC,
    sub_topic=RELAY_SUB_TOPIC,
    client_id=RELAY_CLIENT_ID,
    username=RELAY_USERNAME,
    password=RELAY_PASSWORD,
    logger=logger
)
# 连接MQTT
try:
    while True:
        try:
            relay_controller.connect()
        except Exception as e:
            logger.error(f"MQTT 服务器连接失败: {e} 正在重试")
            time.sleep(1)
            continue
        relay_controller.loop_start()
        time.sleep(1)
        if relay_controller.client.is_connected():
            logger.info("MQTT 服务器已连接")
            break
        else:
            logger.info("MQTT 服务器连接失败，正在重试")
except KeyboardInterrupt:
    logger.info("正在退出...")
    sys.exit(1)

# 创建device_checker
if ADBDEVICECKR_ENABLED:
    device_checker = DeviceMonitor(IP_ADDRESSES, logger,'./log/',THREADTEST_ENABLED,DINGTALK_WEBHOOK_URL,DINGTALK_MESSAGE_TIMEOUT)

# 创建cyclepingtest
if CYCLEPINGTEST_ENABLED:
    cyclepingtest = Cyclepingtest(IP_ADDRESSES, logger,'./log/')

class NetworkMonitor:
    def __init__(self, ip_addresses, timeout):
        self.ip_addresses = ip_addresses
        self.timeout = timeout
        self.success_count = 0  # 添加成功次数计数器

        self.ip_status = dict()
        for ip in self.ip_addresses:
            self.ip_status[ip] = 'Init'

    def ping_ip(self, ip):
        # 使用系统命令 ping 进行网络检测
        response = subprocess.run(['ping', '-n', '1', ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return 'ms' in str(response.stdout)

    def start_test(self):
        # 开始测试
        logger.info("开始测试")

        # 关闭继电器
        relay_controller.turn_off_relay()
        time.sleep(3)  # 等待3秒
        # 打开继电器
        relay_controller.turn_on_relay()

        start_time = time.time()  # 记录开始时间

        while True:
            all_pinged = True  # 假设所有网口都 ping 通了
            for ip in self.ip_addresses:
                if self.ip_status[ip] == 'PingPass':
                    continue
                if not self.ping_ip(ip):
                    all_pinged = False  # 如果有一个网口未 ping 通，则设置为False
                    logger.info(f"IP {ip} 未 ping 通")
                    break
                else:
                    logger.info(f"IP {ip} 已 ping 通")
                    self.ip_status[ip] = 'PingPass'

            if all_pinged:
                elapsed_time = time.time() - start_time
                logger.info(f"所有网口都 ping 通了,耗时{elapsed_time}秒")

                self.success_count += 1  # 增加成功次数
                logger.info(f"测试成功次数: {self.success_count}")

                if CYCLEPINGTEST_ENABLED:
                    ret = cyclepingtest.run(CYCLEPINGTEST_DELAY,CYCLEPINGTEST_TIMES,self.timeout - elapsed_time)
                    elapsed_time = time.time() - start_time

                    if "Pass" in ret:
                        logger.info(f"循环ping测试通过,耗时{elapsed_time}秒")
                    elif "timeout" in ret:
                        logger.info(f"循环ping测试超时,耗时{elapsed_time}秒")
                    elif "Fail" in ret:
                        logger.info(f"循环ping测试失败,耗时{elapsed_time}秒")

                    if 'Fail' in ret:
                        msgData = json.loads(str(DINGTALK_MESSAGE_TIMEOUT))
                        parts = msgData['text']['content'].split(':')
                        parts[1] = "循环ping测试失败，可能是：网络问题"
                        msgData['text']['content'] = ':'.join(parts)
                        requests.post(DINGTALK_WEBHOOK_URL, json=msgData)
                        return
                    
                # 获取当前测试次数
                if ADBDEVICECKR_ENABLED:
                    ret = device_checker.monitor_thread_pass_counts(self.timeout - elapsed_time)
                    elapsed_time = time.time() - start_time

                    if 'timeoutConnect' in ret:
                        logger.error(f"连接超时,耗时{elapsed_time}>{self.timeout}")

                    elif 'timeoutInit' in ret:
                        logger.error(f"获取Thread初始值超时,耗时{elapsed_time}>{self.timeout}")

                    elif 'threadNotAllPass' in ret:
                        logger.error(f"测试超时,耗时{elapsed_time}>{self.timeout}，Thread未全部通过")

                    elif 'AllPass' in ret:
                        logger.info(f"Thread测试全部成功,耗时{elapsed_time}秒")

                    if 'timeout' in ret:
                        ret = device_checker.save_logcat()
                        #如果是系统没有起来，直接退出，保持继电器状态
                        if 'System_startup_failed' in ret:
                            msgData = json.loads(str(DINGTALK_MESSAGE_TIMEOUT))
                            parts = msgData['text']['content'].split(':')
                            parts[1] = " 超时后未获取到launcher，可能是：系统未启动、网络问题"
                            msgData['text']['content'] = ':'.join(parts)
                            requests.post(DINGTALK_WEBHOOK_URL, json=msgData)
                            return
                        #如果是测试软件没有起来，报错后继续测试，保持现状
                        elif 'Test_software_startup_failed' in ret:
                            msgData = json.loads(str(DINGTALK_MESSAGE_TIMEOUT))
                            parts = msgData['text']['content'].split(':')
                            parts[1] = " 超时后停留在launcher，可能是：测试APP未启动"
                            msgData['text']['content'] = ':'.join(parts)
                            requests.post(DINGTALK_WEBHOOK_URL, json=msgData)

                # 延迟断电
                logger.info(f"延迟{TIMEDELAY}秒断电")
                time.sleep(TIMEDELAY)

                # 关闭继电器
                relay_controller.turn_off_relay()
                time.sleep(TIME_RELAYOFF)

                # 打开继电器
                relay_controller.turn_on_relay()

                # 重置计时器
                start_time = time.time()
            else:
                # 检查是否超时
                elapsed_time = time.time() - start_time
                if elapsed_time > self.timeout:
                    logger.error(f"测试超时,耗时{elapsed_time}>{self.timeout}")

                    msgData = json.loads(str(DINGTALK_MESSAGE_TIMEOUT))
                    parts = msgData['text']['content'].split(':')
                    parts[1] = f"超时后有机器超时未Ping通!测试退出"
                    msgData['text']['content'] = ':'.join(parts)        

                    requests.post(DINGTALK_WEBHOOK_URL, json=msgData)
                    return

def handle_exception(exc_type, exc_value, exc_traceback):
    logger.error("未捕获的异常\n")
    logger.error(f"类型: {exc_type.__name__}\n")
    logger.error(f"值: {exc_value}\n")
    logger.error("回溯:\n")
    tb = traceback.format_tb(exc_traceback)
    logger.error("\n".join(tb))

    msgData = json.loads(str(DINGTALK_MESSAGE_ERROR))
    parts = msgData['text']['content'].split(':')
    parts[1] = f"出现异常!{exc_value}。测试退出"
    msgData['text']['content'] = ':'.join(parts)

    requests.post(DINGTALK_WEBHOOK_URL, json=msgData)

if __name__ == "__main__":
    sys.excepthook = handle_exception
    try:
        monitor = NetworkMonitor(IP_ADDRESSES, TIMEOUT)
        monitor.start_test()
        relay_controller.loop_stop()
        relay_controller.close()
    except KeyboardInterrupt:
        logger.info("正在退出...")