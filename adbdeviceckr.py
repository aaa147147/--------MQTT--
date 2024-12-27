import uiautomator2 as u2
import xml.etree.ElementTree as ET
import subprocess
import time
import logging

class DeviceChecker:
    def __init__(self, ip_addresses, logger):
        self.ip_addresses = ip_addresses
        self.thread_pass_num = {ip: None for ip in ip_addresses}
        self.previous_thread_pass_num = {ip: None for ip in ip_addresses}
        self.logger = logger

    def disconnect_device(self, ip):
        #return True
        subprocess.run(['adb', 'disconnect'])

    def connect_device(self, ip):
        subprocess.run(['adb', 'connect', ip])

    def get_thread_pass_num(self, ip):
        try:
            self.connect_device(ip)  # 连接设备
            d = u2.connect(ip)
            elements = d.dump_hierarchy()
            root = ET.fromstring(elements)
            for elem in root.iter():
                #self.logger.info(elem.attrib)
                if elem.attrib.get("resource-id") == 'com.sdmc.facTest:id/thread_num':
                    text = elem.attrib.get('text')
                    #self.logger.info(text)
                    if text:
                        thread_pass_num = int(text.split(':')[1].split('/')[0])
                        thread_total_num = int(text.split(':')[1].split('/')[1])
                        self.logger.info(f'{ip}-Thread测试结果: {thread_pass_num}/{thread_total_num}')
                        self.disconnect_device(ip)  # 断开连接
                        return thread_pass_num
                    
            self.logger.info(f"{ip}-未找到resource-id = com.sdmc.facTest:id/thread_num")
            self.disconnect_device(ip)
        except Exception as e:
            self.logger.info(f"获取{ip}的Thread通过数时发生错误: {e}")
            self.disconnect_device(ip)
        return None

    def update_thread_pass_num(self):
        for ip in self.ip_addresses:
            new_thread_pass_num = self.get_thread_pass_num(ip)
            if new_thread_pass_num is None:
                #self.logger.info(f"{ip}-Thread通过数获取失败")
                return False
            self.thread_pass_num[ip] = new_thread_pass_num
            # 如果第一个IP的thread_pass_num没有变化，则跳出循环
            if self.previous_thread_pass_num[ip] == self.thread_pass_num[ip]:
                break
        return True

    def has_thread_pass_num_changed(self):
        if not self.update_thread_pass_num():
            return False
        all_changed = True
        for ip in self.ip_addresses:
            if self.previous_thread_pass_num[ip] != self.thread_pass_num[ip]:
                continue
            else:
                all_changed = False
                break
        
        if all_changed:
            self.previous_thread_pass_num = self.thread_pass_num.copy()
        
        return all_changed

    def get_current_thread_pass_num_and_update_previous(self):
        if not self.update_thread_pass_num():
            return False
        self.previous_thread_pass_num = self.thread_pass_num.copy()
        return self.thread_pass_num

# 示例使用
if __name__ == "__main__":
    IP_ADDRESSES = [
        '192.168.50.114', '192.168.50.116', '192.168.50.122',
        '192.168.50.221', '192.168.50.225', '192.168.50.228',
        '192.168.50.237', '192.168.50.239'
    ]
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # 创建控制台处理器
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_formatter = logging.Formatter('%(asctime)s - %(message)s')
    stream_handler.setFormatter(stream_formatter)

    logger.addHandler(stream_handler)

    logger.info("测试开始")

    device_checker = DeviceChecker(IP_ADDRESSES, logger)

    # 示例：获取当前的thread_pass_num并更新previous_thread_pass_num
    current_thread_pass_num = device_checker.get_current_thread_pass_num_and_update_previous()
    logger.info(f"当前Thread通过数: {current_thread_pass_num}")

    while True:
        # 更新threadPassNum并检查是否有变化
        if device_checker.has_thread_pass_num_changed():
            logger.info("所有设备的Thread通过数已发生变化。")
            break
        else:
            logger.info("所有设备的Thread通过数未发生变化。")
        time.sleep(1)