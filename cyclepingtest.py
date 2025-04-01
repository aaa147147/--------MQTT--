import subprocess
import time

class Cyclepingtest:
    def __init__(self, device_ips, logger, log_directory):
        self.device_ips = device_ips
        self.logger = logger
        self.log_directory = log_directory

        # 初始化每个IP的状态为 'Init'
        self.ip_status = {ip: 'Init' for ip in self.device_ips}

    def ping_ip(self, ip):
        # 使用系统命令 ping 进行网络检测
        response = subprocess.run(['ping', '-n', '1', ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return 'ms' in str(response.stdout)

    def run(self, CYCLEPINGTEST_DELAY, CYCLEPINGTEST_TIMES, timeout):
        """
        主循环逻辑：
        1. 如果完成所有测试轮次且全部通过，则返回 'pingPass'。
        2. 如果有未通过的测试，持续测试直到超时，返回 'timeoutRun'。
        """
        ping_times = 0
        start_time = time.time()

        while True:
            # 等待下一轮测试
            time.sleep(CYCLEPINGTEST_DELAY)
            ping_times += 1
            self.logger.info(f"开始第{ping_times}轮测试....")


            # 检查是否达到最大测试轮次
            if ping_times > CYCLEPINGTEST_TIMES:
                # 如果所有IP状态均为 'PingPass'，则返回 'pingPass'
                if all(status == 'PingPass' for status in self.ip_status.values()):
                    self.logger.info(f"本次监控结果：AllPass, 测试次数: {ping_times - 1}次")
                    return 'pingPass'

            # 检查是否超时
            if time.time() - start_time > timeout:
                self.logger.info("达到超时时间，退出监控。")
                return 'timeoutRun'

            # 遍历每个IP进行测试
            for ip in self.device_ips:
                # 如果当前IP未通过测试，则持续ping直到ping通或超时
                while self.ip_status[ip] != 'PingPass':
                    if self.ping_ip(ip):
                        self.logger.info(f"{ip} 已 ping 通")
                        self.ip_status[ip] = 'PingPass'
                    else:
                        self.logger.warning(f"{ip} 未 ping 通")
                        # 检查是否超时
                        if time.time() - start_time > timeout:
                            self.logger.info(f"{ip} 达到超时时间，退出监控。")
                            return 'timeoutRun'
                    # 等待一段时间后再次尝试ping
                    time.sleep(CYCLEPINGTEST_DELAY)





