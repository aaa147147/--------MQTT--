import subprocess
import re

class FirewallChecker:
    def __init__(self):
        self.status_patterns = {
            'domain': r'域配置文件\s*设置.*?状态\s+([^\r\n]+)',
            'private': r'专用配置文件\s*设置.*?状态\s+([^\r\n]+)',
            'public': r'公用配置文件\s*设置.*?状态\s+([^\r\n]+)'
        }

    def check_windows_firewall(self):
        """
        检查Windows防火墙状态
        返回一个字典，包含各配置文件的状态
        """
        try:
            # 使用netsh命令检查防火墙状态
            result = subprocess.run(
                ['netsh', 'advfirewall', 'show', 'allprofiles', 'state'],
                capture_output=True,
                text=True,
                encoding='gbk'  # Windows中文系统使用gbk编码
            )
            
            output = result.stdout
            firewall_status = {}
            for profile, pattern in self.status_patterns.items():
                match = re.search(pattern, output, re.DOTALL)
                if match:
                    status = match.group(1).strip().lower()
                    firewall_status[profile] = '开启' if '开启' in status or 'on' in status else '关闭'
            
            return firewall_status
        except Exception as e:
            return {"error": str(e)}

    def is_firewall_on(self):
        """
        检查是否有任意防火墙处于开启状态
        返回: (bool, dict) - (是否有开启的防火墙, 详细状态)
        """
        status = self.check_windows_firewall()
        if "error" in status:
            return False, status
            
        is_on = any(state == '开启' for state in status.values())
        return is_on, status
