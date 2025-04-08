import subprocess
import time

class Cyclepingtest:
    def __init__(self, device_ips, logger, log_directory):
        self.device_ips = device_ips
        self.logger = logger
        self.log_directory = log_directory

    def ping_ip(self, ip):
        response = subprocess.run(['ping', '-n', '1', ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return 'ms' in str(response.stdout)

    def run(self, CYCLEPINGTEST_DELAY, CYCLEPINGTEST_TIMES, timeout):
        start_time = time.time()
        consecutive_success = 0

        while True:
            # 超时检查
            if time.time() - start_time > timeout:
                self.logger.info("达到超时时间，退出监控。")
                return 'timeoutRun'

            # 测试所有IP的连通性
            all_passed = True
            for ip in self.device_ips:
                if not self.ping_ip(ip):
                    self.logger.warning(f"{ip} 未ping通。")
                    all_passed = False
                    break
                self.logger.info(f"{ip} 已ping通。")

            # 处理测试结果
            if all_passed:
                consecutive_success += 1
                if consecutive_success >= CYCLEPINGTEST_TIMES:
                    self.logger.info(f"所有IP连续{CYCLEPINGTEST_TIMES}次测试通过，返回成功。")
                    return 'pingPass'
            else:
                consecutive_success = 0  # 重置连续成功计数
                # 若为多次测试模式，立即返回失败
                if CYCLEPINGTEST_TIMES > 1:
                    self.logger.info("存在未通过的IP，返回失败。")
                    return 'pingFailed'

            # 等待下一轮测试
            time.sleep(CYCLEPINGTEST_DELAY)