import subprocess
import uiautomator2 as u2
from typing import Dict, Optional
from event_manager import EventType

class adb_cmd_test:  #(pingTestcfg, logger,log_folder, event_manager)
    def __init__(self, pingTestcfg, logger, log_directory, event_manager=None):
        self.device_ips = pingTestcfg.IP_ADDRESSES
        self.logger = logger
        self.log_directory = log_directory
        self.event_manager = event_manager
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
            ui = u2.connect(ip + ':5555')
            if ui.info.get('productName'):
                self.logger.info(f"设备 {ip} 连接成功")
                return ui
            self.logger.error(f"无法获取设备的产品名称:{ip}")
            return None
        except Exception as e:
            self.logger.error(f"设备 {ip} 连接失败: {e}")
            return None



