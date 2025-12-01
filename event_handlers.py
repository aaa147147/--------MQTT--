import json
import requests
import sys

from event_manager import EventType, Event, resolve_event_action


def _compose_dingtalk_message(template, content_text):
    msgData = json.loads(str(template))
    text_obj = msgData.get('text')
    if not isinstance(text_obj, dict):
        msgData['text'] = {}
    content = msgData['text'].get('content', '')
    parts = content.split(':', 1)
    if len(parts) == 2:
        parts[1] = content_text
        msgData['text']['content'] = ':'.join(parts)
    else:
        msgData['text']['content'] = content_text
    return msgData


def notify_dingtalk(pingTestcfg, content_text):
    msgData = _compose_dingtalk_message(pingTestcfg.DINGTALK_MESSAGE_TIMEOUT, content_text)
    requests.post(pingTestcfg.DINGTALK_WEBHOOK_URL, json=msgData)

def register_handlers(event_manager, pingTestcfg, logger):

    #==PingTest Events==================================================================================================================
    @event_manager.on(EventType.PING_TIMEOUT)
    def _on_test_timeout(event: Event):
        action = resolve_event_action(pingTestcfg, EventType.PING_TIMEOUT)
        msg=f"测试超时,耗时{event.data['elapsed']}>{pingTestcfg.TIMEOUT},没ping通的IP：{event.data['PingFailed_IP']}，{action}"
        logger.error(msg)
        notify_dingtalk(pingTestcfg,msg)

    #==adbdeviceckr Events==================================================================================================================
    @event_manager.on(EventType.ADB_DEVICE_TIMEOUT_INIT)
    def _on_device_timeout_connect(event: Event):
        action = resolve_event_action(pingTestcfg, EventType.ADB_DEVICE_TIMEOUT_INIT)
        msg=f"ADBCKR初始化失败,耗时{event.data['elapsed']},Failed_IP：{event.data['initFailed_IP']}，{action}"
        logger.error(msg)
        if action == 'ignore':
            return
        else:
            notify_dingtalk(pingTestcfg,msg)
            sys.exit(1)
        

    @event_manager.on(EventType.ADB_DEVICE_THREAD_NOT_ALL_PASS)
    def _on_device_thread_not_all_pass(event: Event):
        action = resolve_event_action(pingTestcfg, EventType.ADB_DEVICE_THREAD_NOT_ALL_PASS)
        msg=f"Thread测试未全部通过,耗时{event.data['elapsed']},Failed_IP：{event.data['Failed_IP']}，{action}"
        logger.error(msg)
        if action == 'ignore':
            return
        else:
            notify_dingtalk(pingTestcfg,msg)
            sys.exit(1)
    @event_manager.on(EventType.ADB_SYSTEM_STARTUP_FAILED)
    def _on_system_startup_failed(event: Event):
        action = resolve_event_action(pingTestcfg, EventType.ADB_SYSTEM_STARTUP_FAILED)
        msg = f"系统启动失败,'Failed_IP'：{event.data['Failed_IP']}，{action}"
        logger.error(msg)
        if action == 'ignore':
            return
        else:
            notify_dingtalk(pingTestcfg,msg)
            sys.exit(1)

    @event_manager.on(EventType.ADB_TEST_SOFTWARE_STARTUP_FAILED)
    def _on_test_software_startup_failed(event: Event):
        action = resolve_event_action(pingTestcfg, EventType.ADB_TEST_SOFTWARE_STARTUP_FAILED)
        msg = f"测试软件启动失败,Failed_IP：{event.data['Failed_IP']},当前界面：{event.data['package_name']}，{action}"
        logger.error(msg)
        if action == 'ignore':
            return
        else:
            notify_dingtalk(pingTestcfg,msg)
            sys.exit(1)

    #==cyclepingtest Events==================================================================================================================
    @event_manager.on(EventType.CYCLEPING_PASS)
    def _on_cycle_pass(event: Event):
        logger.info(f"循环ping测试通过,耗时{event.data['elapsed']}秒")

    @event_manager.on(EventType.CYCLEPING_FAIL)
    def _on_cycle_fail(event: Event):
        logger.info(f"循环ping测试失败,耗时{event.data['elapsed']}秒")

    @event_manager.on(EventType.CYCLEPING_TIMEOUT)
    def _on_cycle_timeout(event: Event):
        action = resolve_event_action(pingTestcfg, EventType.CYCLEPING_TIMEOUT)
        suffix = "，已重启" if action == "restart" else "，测试退出"
        notify_dingtalk(
            pingTestcfg,
            f"循环ping测试超时，可能是：网络问题{suffix}"
        )

    #==未捕获异常 Events==================================================================================================================
    @event_manager.on(EventType.UNCAUGHT_EXCEPTION)
    def _on_uncaught_exception(event: Event):
        msg = f"出现未捕获异常,exc_type：{event.data['exc_type']},exc_value：{event.data['exc_value']},trace{event.data['trace']}"
        notify_dingtalk(pingTestcfg,msg)
        sys.exit(1)
