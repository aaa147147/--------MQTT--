import os
import subprocess
import time
import logging
import uiautomator2 as u2
import xml.etree.ElementTree as ET
import datetime
from typing import Dict, Any, Optional
from event_manager import EventType

class DeviceMonitor:
    THREAD_NUM_RESOURCE_ID = 'com.sdmc.facTest:id/thread_num'
    LAUNCHER_PKG = 'com.google.android.apps.tv.launcherx'

    def __init__(self, device_ips, logger, log_directory,thread_test_enable,DINGTALK_WEBHOOK_URL,DINGTALK_MESSAGE_TIMEOUT, event_manager=None):
        self.device_ips = device_ips
        self.previous_thread_pass_counts: Dict[str, Optional[int]] = {ip: None for ip in self.device_ips}
        self.current_thread_pass_counts: Dict[str, Optional[int]] = {ip: None for ip in self.device_ips}
        self.ui_devices: Dict[str, Optional[u2.Device]] = {ip: None for ip in self.device_ips}
        self.logger = logger
        self.log_directory = log_directory
        self._ensure_log_directory_exists()
        self.thread_test_enable = thread_test_enable
        self.dingtalk_webhook_url = DINGTALK_WEBHOOK_URL
        self.dingtalk_message_timeout = DINGTALK_MESSAGE_TIMEOUT
        self.event_manager = event_manager
    def _ensure_log_directory_exists(self):
        if not os.path.exists(self.log_directory):
            os.makedirs(self.log_directory)

    def _execute_command(self, command):
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Command failed: {command} - {e}")

    def _disconnect_device(self, ip):
        self._execute_command(['adb', 'disconnect', ip])

    def adb_bugreport(self, ip):
        self._execute_command(['adb', '-s', ip,'bugreport'])

    def _connect_device(self, ip):
        try:
            subprocess.run(['adb', 'connect', ip], check=True)
            ui = u2.connect(ip)
            if ui.info.get('productName'):
                self.logger.info(f"设备 {ip} 连接成功")
                return ui
            self.logger.error(f"设备 {ip} 连接失败")
            return None
        except Exception as e:
            self.logger.error(f"设备 {ip} 连接失败: {e}")
            return None

    def _update_ui_data(self, ip):
        max_retries = 3
        retries = 0
        while retries < max_retries:
            try:
                ui = self.ui_devices[ip]
                if ui is None:
                    ui = self._connect_device(ip)
                    self.ui_devices[ip] = ui
                    if ui is None:
                        raise RuntimeError('连接失败')
                xml_str = ui.dump_hierarchy()
                return ET.fromstring(xml_str)
            except Exception as e:
                self.logger.error(f"设备 {ip} 获取 UI 数据失败: {e}, 重试 {retries + 1}/{max_retries}")
                self.ui_devices[ip] = self._connect_device(ip)
                retries += 1
        self.logger.error(f"设备 {ip} 获取 UI 数据失败，已达到最大重试次数 {max_retries}")
        return None
    def _get_current_package_name(self, ip):
        root = self._update_ui_data(ip)
        if root is None:
            return None
        try:
            return root[0].attrib.get('package')
        except Exception as e:
            self.logger.error(f"获取{ip}的包名时发生错误: {e}")
            self._disconnect_device(ip)
            return None

    def get_thread_pass_count(self, ip):
        root = self._update_ui_data(ip)
        if root is None:
            return None
        try:
            for elem in root.iter():
                if elem.attrib.get("resource-id") == self.THREAD_NUM_RESOURCE_ID:
                    text = elem.attrib.get('text')
                    if not text:
                        self.logger.info(f"{ip}-未找到resource-id = {self.THREAD_NUM_RESOURCE_ID}")
                        break
                    try:
                        part = text.split(':', 1)[1]
                        thread_pass_count = int(part.split('/')[0])
                        self.logger.info(f"{ip}-Thread测试结果: {thread_pass_count}/{part.split('/')[1]}")
                        return thread_pass_count
                    except Exception:
                        self.logger.error(f"{ip}-Thread文本解析失败: {text}")
                        return None
            else:
                self.logger.info(f"{ip}-未找到resource-id = {self.THREAD_NUM_RESOURCE_ID}")
        except Exception as e:
            self.logger.error(f"获取{ip}的Thread通过数时发生错误: {e}")
        return None

    def _emit(self, event_type: EventType, data: Dict[str, Any]):
        if self.event_manager:
            self.event_manager.emit(event_type, data)

    def monitor_thread_pass_counts(self, timeout):
        start_time = time.time()
        self.logger.info(f"开始监控Thread测试通过次数，超时时间为{timeout}秒。")
        self.previous_thread_pass_counts = {ip: None for ip in self.device_ips}
        self.current_thread_pass_counts = {ip: None for ip in self.device_ips}
        self.ui_devices = {ip: None for ip in self.device_ips}

        while True:
            all_initialized = True
            for ip in self.device_ips:
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    self.logger.info("达到超时时间，退出监控。")
                    self._emit(EventType.DEVICE_TIMEOUT_CONNECT, {"elapsed": elapsed})
                    ret2 = self.save_logcat()
                    if 'System_startup_failed' in ret2:
                        self._emit(EventType.SYSTEM_STARTUP_FAILED, {})
                    elif 'Test_software_startup_failed' in ret2:
                        self._emit(EventType.TEST_SOFTWARE_STARTUP_FAILED, {})
                    return 'timeoutConnect'
                if self.ui_devices[ip] is None:
                    self.ui_devices[ip] = self._connect_device(ip)
                if self.ui_devices[ip] is None:
                    all_initialized = False
            if all_initialized:
                self.logger.info(f"所有设备已连接成功,耗时{time.time() - start_time:.2f}秒")
                break

        while True:
            all_initialized = True
            for ip in self.device_ips:
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    self.logger.info("达到超时时间，退出监控。")
                    self._emit(EventType.DEVICE_TIMEOUT_INIT, {"elapsed": elapsed})
                    ret2 = self.save_logcat()
                    if 'System_startup_failed' in ret2:
                        self._emit(EventType.SYSTEM_STARTUP_FAILED, {})
                    elif 'Test_software_startup_failed' in ret2:
                        self._emit(EventType.TEST_SOFTWARE_STARTUP_FAILED, {})
                    return 'timeoutInit'
                if self.previous_thread_pass_counts[ip] is None:
                    self.previous_thread_pass_counts[ip] = self.get_thread_pass_count(ip)
                if self.previous_thread_pass_counts[ip] is None:
                    all_initialized = False
                else:
                    self.logger.info(f"{ip}-Thread初始次数已获取-{self.previous_thread_pass_counts[ip]}")
            if all_initialized:
                self.logger.info(f"所有设备的Thread测试通过次数已初始化:{self.previous_thread_pass_counts}")
                break

        while True and self.thread_test_enable:
            all_changed = True
            for ip in self.device_ips:
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    self.logger.info("达到超时时间，退出监控。")
                    self._emit(EventType.DEVICE_THREAD_NOT_ALL_PASS, {"elapsed": elapsed})
                    return 'threadNotAllPass'
                new_thread_pass_count = self.get_thread_pass_count(ip)
                if new_thread_pass_count is None:
                    continue
                self.current_thread_pass_counts[ip] = new_thread_pass_count
                if self.previous_thread_pass_counts[ip] == self.current_thread_pass_counts[ip]:
                    all_changed = False
                else:
                    self.logger.info(f"{ip}-Thread测试次数改变，从{self.previous_thread_pass_counts[ip]}变成{self.current_thread_pass_counts[ip]}")
            if all_changed:
                self.logger.info(f"所有设备的Thread通过数已发生变化:{self.current_thread_pass_counts}")
                break
        elapsed = time.time() - start_time
        self._emit(EventType.DEVICE_ALL_PASS, {"elapsed": elapsed})
        return 'AllPass'

    def save_logcat(self):
        result = 'Pass'
        for ip in self.device_ips:
            if self.get_thread_pass_count(ip) is None:
                current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                try:
                    logcat_file_path = os.path.join(self.log_directory, f'{current_time}_{ip}_logcat.txt')
                    with open(logcat_file_path, 'w') as logcat_file:
                        subprocess.run(['adb', '-s', ip, 'logcat', '-d'], stdout=logcat_file, timeout=30)
                    self.logger.info(f"Logcat for {ip} saved to {logcat_file_path}")
                except Exception as e:
                    self.logger.error(f"{ip}-Logcat保存失败: {e}")

                package_name = self._get_current_package_name(ip)
                if package_name == self.LAUNCHER_PKG:
                    result += '--' + f'Test_software_startup_failed'
                else:
                    result += '--' + 'System_startup_failed'
        return result

def setup_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # 创建控制台处理器
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_formatter = logging.Formatter('%(asctime)s - %(message)s')
    stream_handler.setFormatter(stream_formatter)

    logger.addHandler(stream_handler)
    return logger

