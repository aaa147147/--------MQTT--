

import subprocess
import time






class Cyclepingtest:
    def __init__(self, device_ips, logger, log_directory):
        self.device_ips = device_ips
        self.logger = logger
        self.log_directory = log_directory
    def ping_ip(self, ip):
        # 使用系统命令 ping 进行网络检测
        response = subprocess.run(['ping', '-n', '1', ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return 'ms' in str(response.stdout)

    def run(self,CYCLEPINGTEST_DELAY,CYCLEPINGTEST_TIMES,timeout):
        #ping通后等20秒再ping,这样循环，ping的时间和次数可以调
        pingTimes = 0
        start_time = time.time()
        while True:
            pingTimes = pingTimes + 1
            if pingTimes >= CYCLEPINGTEST_TIMES:
                self.logger.info(f"本次监控结果：AllPass,测试次数:{pingTimes}次")                
                return 'pingPass'
            
            for ip in self.device_ips:
                if time.time() - start_time > timeout:
                    self.logger.info("达到超时时间，IP均能正常ping通，退出监控。")
                    return 'timeoutRun'
                        
                if self.ping_ip(ip):
                    self.logger.info(f"{ip} is online.")
                else:
                    self.logger.warning(f"{ip} is offline.")
                    return 'pingFailed'
            time.sleep(CYCLEPINGTEST_DELAY)






