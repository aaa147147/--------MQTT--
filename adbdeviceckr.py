import os
import subprocess
import time
import logging
import uiautomator2 as u2
import xml.etree.ElementTree as ET
import datetime

class DeviceMonitor:
    def __init__(self, device_ips, logger, log_directory='./log'):
        self.device_ips = device_ips
        self.previous_thread_pass_counts = {ip: None for ip in self.device_ips}
        self.current_thread_pass_counts = {ip: None for ip in self.device_ips}
        self.uiAuto_devices = {ip: None for ip in self.device_ips}
        self.logger = logger
        self.log_directory = log_directory
        self._ensure_log_directory_exists()

        # # 连接所有设备
        # while True:
        #     all_initialized = True
        #     for ip in self.device_ips:

        #         if self.uiAuto_devices[ip] is None:
        #             self.uiAuto_devices[ip] = self._connect_device(ip)

        #         if self.uiAuto_devices[ip] is None:
        #             all_initialized = False

        #     if all_initialized:
        #         self.logger.info(f"所有设备已连接成功")
        #         break

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

    def _connect_device(self, ip):
        try:
            subprocess.run(['adb', 'connect', ip], check=True)
            uiAuto = u2.connect(ip)
            # 检查设备是否连接成功
            if uiAuto.info.get('productName'):
                self.logger.info(f"设备 {ip} 连接成功")
                return uiAuto
            else:
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
                uiElements = self.uiAuto_devices[ip].dump_hierarchy()
                uiElementsRoot = ET.fromstring(uiElements)
                return uiElementsRoot
            except Exception as e:
                self.logger.error(f"设备 {ip} 获取 UI 数据失败: {e}, 尝试重连并重试 ({retries + 1}/{max_retries})")
                self._connect_device(ip)
                retries += 1

        self.logger.error(f"设备 {ip} 获取 UI 数据失败，已达到最大重试次数 {max_retries}")
        return None
    def _get_current_package_name(self, ip):
        uiElementsRoot = self._update_ui_data(ip)
        if uiElementsRoot is None:
            return None
        try:
            package_name = uiElementsRoot[0].attrib.get('package')
            return package_name
        except Exception as e:
            self.logger.error(f"获取{ip}的包名时发生错误: {e}")
            self._disconnect_device(ip)
        return None

    def get_thread_pass_count(self, ip):
        uiElementsRoot = self._update_ui_data(ip)
        if uiElementsRoot is None:
            return None
        try:
            # 直接在get_thread_pass_count方法中查找元素文本
            for elem in uiElementsRoot.iter():
                if elem.attrib.get("resource-id") == 'com.sdmc.facTest:id/thread_num':
                    text = elem.attrib.get('text')
                    if text:
                        thread_pass_count, thread_total_count = map(int, text.split(':')[1].split('/'))
                        print(f'{ip}-Thread测试结果: {thread_pass_count}/{thread_total_count}')
                        return thread_pass_count
                    else:
                        self.logger.info(f"{ip}-未找到resource-id = com.sdmc.facTest:id/thread_num")
                    break
            else:
                self.logger.info(f"{ip}-未找到resource-id = com.sdmc.facTest:id/thread_num")
        except Exception as e:
            self.logger.error(f"获取{ip}的Thread通过数时发生错误: {e}")
        return None

    def monitor_thread_pass_counts(self, timeout):
        start_time = time.time()
        self.logger.info(f"开始监控Thread测试通过次数，超时时间为{timeout}秒。")
        self.previous_thread_pass_counts = {ip: None for ip in self.device_ips}
        self.current_thread_pass_counts = {ip: None for ip in self.device_ips}
        self.uiAuto_devices = {ip: None for ip in self.device_ips}

        # 连接所有设备
        while True:
            all_initialized = True
            for ip in self.device_ips:
                if time.time() - start_time > timeout:
                    self.logger.info("达到超时时间，退出监控。")
                    return 'timeoutConnect'

                if self.uiAuto_devices[ip] is None:
                    self.uiAuto_devices[ip] = self._connect_device(ip)

                if self.uiAuto_devices[ip] is None:
                    all_initialized = False

            if all_initialized:
                self.logger.info(f"所有设备已连接成功,耗时{time.time() - start_time:.2f}秒")
                break

        # 初始化所有设备的Thread测试通过次数
        while True:
            all_initialized = True
            for ip in self.device_ips:
                if time.time() - start_time > timeout:
                    self.logger.info("达到超时时间，退出监控。")
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

        # 监控所有Thread测试通过次数
        while True:
            all_changed = True
            for ip in self.device_ips:
                if time.time() - start_time > timeout:
                    self.logger.info("达到超时时间，退出监控。")
                    return 'threadNotAllPass'

                new_thread_pass_count = self.get_thread_pass_count(ip)
                if new_thread_pass_count is None:
                    continue
                else:
                    self.current_thread_pass_counts[ip] = new_thread_pass_count

                if self.previous_thread_pass_counts[ip] == self.current_thread_pass_counts[ip]:
                    all_changed = False
                else:
                    self.logger.info(f"{ip}-Thread测试次数改变，从{self.previous_thread_pass_counts[ip]}变成{self.current_thread_pass_counts[ip]}")
                    
            if all_changed:
                self.logger.info(f"所有设备的Thread通过数已发生变化:{self.current_thread_pass_counts}")
                break
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
                if package_name == 'com.google.android.apps.tv.launcherx':
                    result += '--' + 'Test_software_startup_failed'
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

if __name__ == "__main__":
    DEVICE_IPS = [
        '192.168.50.114', '192.168.50.116', '192.168.50.122',
        '192.168.50.221', '192.168.50.225', '192.168.50.228',
        '192.168.50.237', '192.168.50.239'
    ]
    logger = setup_logger()
    logger.info("测试开始")

    device_monitor = DeviceMonitor(DEVICE_IPS, logger)

    # 示例：监控Thread通过数变化，设置超时时间为60秒
    result = device_monitor.monitor_thread_pass_counts(timeout=60)
    logger.info(f"监控结果: {result}")

    # 如果监控未成功，保存logcat
    if result != 'AllPass':
        device_monitor.save_logcat()