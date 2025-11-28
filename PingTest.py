import time
import logging
from pythonping import ping
import sys
import ctypes
import datetime
import traceback
import os
from event_manager import EventType, EventManager
from event_policy import should_restart, resolve_event_action
from event_handlers import register_handlers

from config_loader import load_config
from mqtt_relay_controller import RelayController  # 引入RelayController类
from adbdeviceckr import DeviceMonitor
from cyclepingtest import Cyclepingtest

# 设置控制台窗口标题
ctypes.windll.kernel32.SetConsoleTitleW(f'PingTest-V03 Copyright © 2024 #EE_Lixin. All Rights Reserved. - [{os.path.basename(os.getcwd())}]')

# 配置日志，创建文件处理器，创建控制台处理器，添加处理器到日志记录器
log_folder = './log'
if not os.path.exists(log_folder):
    os.makedirs(log_folder)
    print(f"文件夹 {log_folder} 已创建")
else:
    print(f"文件夹 {log_folder} 已存在")
LOG_FILE = f"{log_folder}/{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}-logfile.txt"
logger = logging.getLogger()
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(LOG_FILE, mode='w')
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(message)s')
file_handler.setFormatter(file_formatter)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_formatter = logging.Formatter('%(asctime)s - %(message)s')
stream_handler.setFormatter(stream_formatter)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# 加载配置项
pingTestcfg = load_config(logger)

# 创建事件管理器
event_manager = EventManager()
register_handlers(event_manager, pingTestcfg, logger)

# 配置继电器MQTT
relay_controller = RelayController(broker=pingTestcfg.RELAY_BROKER,port=pingTestcfg.RELAY_PORT,pub_topic=pingTestcfg.RELAY_PUB_TOPIC,
    sub_topic=pingTestcfg.RELAY_SUB_TOPIC,client_id=pingTestcfg.RELAY_CLIENT_ID,username=pingTestcfg.RELAY_USERNAME,
    password=pingTestcfg.RELAY_PASSWORD,logger=logger,message_check_name = pingTestcfg.RELAY_message_check_name,
    message_check_key = pingTestcfg.RELAY_message_check_key,message_check_value = pingTestcfg.RELAY_message_check_value)

# 创建device_checker
if pingTestcfg.ADBDEVICECKR_ENABLED:
    device_checker = DeviceMonitor(pingTestcfg.IP_ADDRESSES, logger,'./log/',pingTestcfg.THREADTEST_ENABLED,pingTestcfg.DINGTALK_WEBHOOK_URL,pingTestcfg.DINGTALK_MESSAGE_TIMEOUT, event_manager)

# 创建cyclepingtest
if pingTestcfg.CYCLEPINGTEST_ENABLED:
    cyclepingtest = Cyclepingtest(pingTestcfg.IP_ADDRESSES, logger,'./log/', pingTestcfg, event_manager)


class NetworkMonitor:
    def __init__(self, ip_addresses, timeout, event_manager):
        self.ip_addresses = ip_addresses
        self.timeout = timeout
        self.success_count = 0
        self.event_manager = event_manager
        self.ip_status = dict()

    def ping_ip(self, ip):
        ret = ping(ip, count=1, timeout=2, size=32, verbose=True)
        return ret.success()
    def all_ping(self):
        all_pinged = True # 假设所有网口都 ping 通了
        #初始化状态
        for ip in self.ip_addresses:
            self.ip_status[ip] = 'Init'        
        for ip in self.ip_addresses:
            if not self.ping_ip(ip):
                all_pinged = False
                self.event_manager.emit_async(EventType.PING_FAIL, {"ip": ip})
                break
            else:
                self.event_manager.emit_async(EventType.PING_SUCCESS, {"ip": ip})
                self.ip_status[ip] = 'PingPass'
        return all_pinged
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
            if self.all_ping():
                elapsed_time = time.time() - start_time
                self.event_manager.emit(EventType.PING_PASS, {"elapsed": elapsed_time})
                self.success_count += 1
                logger.info(f"测试成功次数: {self.success_count}")

                # CYCLEPINGTEST-循环ping测试
                if pingTestcfg.CYCLEPINGTEST_ENABLED:
                    ret = cyclepingtest.run(pingTestcfg.CYCLEPINGTEST_DELAY,pingTestcfg.CYCLEPINGTEST_TIMES,self.timeout - elapsed_time)
                    if ret == 'timeoutRun':
                        action = resolve_event_action(pingTestcfg, EventType.CYCLEPING_TIMEOUT)
                        if action == 'restart':
                            start_time = time.time()
                        else:
                            return
                    if ret == 'pingFailed':
                        action = resolve_event_action(pingTestcfg, EventType.CYCLEPING_FAIL)
                        if action == 'restart':
                            start_time = time.time()
                        else:
                            return
                # ADBDEVICECKR-用adb检查设备各个状态
                if pingTestcfg.ADBDEVICECKR_ENABLED:
                    device_checker.monitor_thread_pass_counts(self.timeout - elapsed_time)

                # 延迟断电、然后再延迟上电
                logger.info(f"延迟{pingTestcfg.TIMEDELAY}秒断电")
                time.sleep(pingTestcfg.TIMEDELAY)
                relay_controller.turn_off_relay()
                time.sleep(pingTestcfg.TIME_RELAYOFF)
                relay_controller.turn_on_relay()

                # 重置计时器
                start_time = time.time()
            else:
                # 检查是否超时
                elapsed_time = time.time() - start_time
                if elapsed_time > self.timeout:
                    self.event_manager.emit(EventType.PING_TIMEOUT, {"elapsed": elapsed_time, "PingFailed_IP": [ip for ip, s in self.ip_status.items() if s != "PingPass"]})
                    
                    #判断重新测试还是停止
                    action = resolve_event_action(pingTestcfg, EventType.PING_TIMEOUT)
                    if action == 'restart':
                        while True:  
                            #如果全部ping通了，就重新开始测试
                            if self.all_ping():
                                break
                            if time.time() - start_time > 2 * 60 * 60:  #每隔2小时发一次消息
                                self.event_manager.emit(EventType.PING_TIMEOUT, {"elapsed": elapsed_time, "PingFailed_IP": [ip for ip, s in self.ip_status.items() if s != "PingPass"]})
                                start_time = time.time()
                            time.sleep(1)
                        start_time = time.time()
                    else:
                        return

def handle_exception(exc_type, exc_value, exc_traceback):
    tb = traceback.format_tb(exc_traceback)
    event_manager.emit(EventType.UNCAUGHT_EXCEPTION, {"exc_type": exc_type.__name__, "exc_value": str(exc_value), "trace": "\n".join(tb)})

if __name__ == "__main__":
    sys.excepthook = handle_exception
    try:
        monitor = NetworkMonitor(pingTestcfg.IP_ADDRESSES, pingTestcfg.TIMEOUT, event_manager)
        monitor.start_test()
        relay_controller.loop_stop()
        relay_controller.close()
    except KeyboardInterrupt:
        logger.info("正在退出...")
