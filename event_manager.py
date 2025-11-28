import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, List, Any
from concurrent.futures import ThreadPoolExecutor


class EventType(Enum):
    PING_SUCCESS = "ping_success"     #单个ip已ping通
    PING_FAIL = "ping_fail"           #单个ip未ping通
    PING_PASS = "ping_pass"           #所有ip都ping通
    PING_TIMEOUT = "ping_timeout"     #测试超时

    CYCLEPING_PASS = "cycleping_pass"        #循环ping测试通过
    CYCLEPING_FAIL = "cycleping_fail"        #循环ping测试不通过
    CYCLEPING_TIMEOUT = "cycleping_timeout"  #循环ping超时

    ADB_DEVICE_TIMEOUT_CONNECT = "adb_device_timeout_connect"           #设备连接超时
    ADB_DEVICE_TIMEOUT_INIT = "adb_device_timeout_init"                 #设备初始化超时
    ADB_DEVICE_THREAD_NOT_ALL_PASS = "adb_device_thread_not_all_pass"   #设备线程未全部通过
    ADB_DEVICE_ALL_PASS = "adb_device_all_pass"                         #设备全部通过
    ADB_SYSTEM_STARTUP_FAILED = "adb_system_startup_failed"               #系统启动失败
    ADB_TEST_SOFTWARE_STARTUP_FAILED = "adb_test_software_startup_failed" #测试软件启动失败


    UNCAUGHT_EXCEPTION = "uncaught_exception"                     #未捕获的异常


@dataclass
class Event:
    event_type: EventType
    data: Dict[str, Any]


class EventManager:
    def __init__(self):
        self.handlers: Dict[EventType, List[Callable]] = {t: [] for t in EventType}
        self.executor = ThreadPoolExecutor(max_workers=4)

    def register_handler(self, event_type: EventType, handler: Callable):
        self.handlers[event_type].append(handler)

    def on(self, event_type: EventType):
        def decorator(func: Callable):
            self.register_handler(event_type, func)
            return func
        return decorator

    def publish(self, event: Event):
        for handler in self.handlers.get(event.event_type, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.run(handler(event))
                else:
                    handler(event)
            except Exception:
                pass

    def emit(self, event_type: EventType, data: Dict[str, Any]):
        self.publish(Event(event_type, data))

    def publish_async(self, event: Event):
        for handler in self.handlers.get(event.event_type, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    self.executor.submit(asyncio.run, handler(event))
                else:
                    self.executor.submit(handler, event)
            except Exception:
                pass

    def emit_async(self, event_type: EventType, data: Dict[str, Any]):
        self.publish_async(Event(event_type, data))

