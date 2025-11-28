import subprocess
import time
from event_manager import EventType

class Cyclepingtest:
    def __init__(self, device_ips, logger, log_directory, pingTestcfg=None, event_manager=None):
        self.device_ips = device_ips
        self.logger = logger
        self.log_directory = log_directory
        self.pingTestcfg = pingTestcfg
        self.event_manager = event_manager

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
                if self.event_manager:
                    self.event_manager.emit(EventType.CYCLEPING_TIMEOUT, {})
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
                    if self.event_manager:
                        self.event_manager.emit(EventType.CYCLEPING_PASS, {"elapsed": time.time() - start_time})
                    return 'pingPass'
            else:
                consecutive_success = 0  # 重置连续成功计数
                # 若为多次测试模式，立即返回失败
                if CYCLEPINGTEST_TIMES > 1:
                    self.logger.info("存在未通过的IP，返回失败。")
                    if self.event_manager:
                        self.event_manager.emit(EventType.CYCLEPING_FAIL, {"elapsed": time.time() - start_time})
                        if self.pingTestcfg:
                            import json, requests
                            msgData = json.loads(str(self.pingTestcfg.DINGTALK_MESSAGE_TIMEOUT))
                            parts = msgData['text']['content'].split(':')
                            parts[1] = "循环ping测试失败，可能是：网络问题"
                            msgData['text']['content'] = ':'.join(parts)
                            requests.post(self.pingTestcfg.DINGTALK_WEBHOOK_URL, json=msgData)
                    return 'pingFailed'

            # 等待下一轮测试
            time.sleep(CYCLEPINGTEST_DELAY)
