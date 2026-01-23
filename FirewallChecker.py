try:
    import win32com.client
    import pythoncom
except ImportError:
    win32com = None

class FirewallChecker:
    def __init__(self):
        # Profile types bitmask constants
        self.NET_FW_PROFILE2_DOMAIN = 1
        self.NET_FW_PROFILE2_PRIVATE = 2
        self.NET_FW_PROFILE2_PUBLIC = 4
        
        self.profile_map = {
            'domain': self.NET_FW_PROFILE2_DOMAIN,
            'private': self.NET_FW_PROFILE2_PRIVATE,
            'public': self.NET_FW_PROFILE2_PUBLIC
        }

    def check_windows_firewall(self):
        """
        检查Windows防火墙状态 (使用 Windows COM API)
        返回一个字典，包含各配置文件的状态
        """
        if win32com is None:
            return {"error": "Missing dependency: pywin32. Please install it using 'pip install pywin32'"}

        try:
            # 初始化 COM 库 (确保在多线程环境下正常工作)
            pythoncom.CoInitialize()
            
            # 创建防火墙策略对象
            fw_policy = win32com.client.Dispatch("HNetCfg.FwPolicy2")
            
            firewall_status = {}
            for name, profile_type in self.profile_map.items():
                is_enabled = fw_policy.FirewallEnabled(profile_type)
                firewall_status[name] = '开启' if is_enabled else '关闭'
            
            return firewall_status
            
        except Exception as e:
            return {"error": str(e)}
        finally:
            # 释放 COM 资源
            try:
                pythoncom.CoUninitialize()
            except:
                pass

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
