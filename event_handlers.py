import json
import requests
from event_manager import EventType, Event
from event_policy import resolve_event_action


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

    @event_manager.on(EventType.PING_SUCCESS)
    def _on_ping_success(event: Event):
        logger.debug(f"IP {event.data['ip']} 已 ping 通")

    @event_manager.on(EventType.PING_FAIL)
    def _on_ping_fail(event: Event):
        logger.debug(f"IP {event.data['ip']} 未 ping 通")

    @event_manager.on(EventType.PING_PASS)
    def _on_all_pinged(event: Event):
        logger.info(f"所有网口都 ping 通了,耗时{event.data['elapsed']}秒")

    @event_manager.on(EventType.PING_TIMEOUT)
    def _on_test_timeout(event: Event):
        action = resolve_event_action(pingTestcfg, EventType.PING_TIMEOUT)
        msg=f"测试超时,耗时{event.data['elapsed']}>{pingTestcfg.TIMEOUT},没ping通的IP：{event.data['PingFailed_IP']}，{action}"
        logger.error(msg)
        notify_dingtalk(pingTestcfg,msg)

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
    @event_manager.on(EventType.ADB_DEVICE_TIMEOUT_CONNECT)
    def _on_device_timeout_connect(event: Event):
        logger.error(f"连接超时,耗时{event.data['elapsed']}>{pingTestcfg.TIMEOUT}")

    @event_manager.on(EventType.ADB_DEVICE_TIMEOUT_INIT)
    def _on_device_timeout_init(event: Event):
        logger.error(f"获取Thread初始值超时,耗时{event.data['elapsed']}>{pingTestcfg.TIMEOUT}")

    @event_manager.on(EventType.ADB_DEVICE_THREAD_NOT_ALL_PASS)
    def _on_device_thread_not_all_pass(event: Event):
        logger.error(f"测试超时,耗时{event.data['elapsed']}>{pingTestcfg.TIMEOUT}，Thread未全部通过")

    @event_manager.on(EventType.ADB_DEVICE_ALL_PASS)
    def _on_device_all_pass(event: Event):
        logger.info(f"Thread测试全部成功,耗时{event.data['elapsed']}秒")

    @event_manager.on(EventType.ADB_SYSTEM_STARTUP_FAILED)
    def _on_system_startup_failed(event: Event):
        notify_dingtalk(
            pingTestcfg,
            " 超时后未获取到launcher，可能是：系统未启动、网络问题"
        )

    @event_manager.on(EventType.ADB_TEST_SOFTWARE_STARTUP_FAILED)
    def _on_test_software_startup_failed(event: Event):
        notify_dingtalk(
            pingTestcfg,
            " 超时后停留在launcher，可能是：测试APP未启动"
        )

    @event_manager.on(EventType.UNCAUGHT_EXCEPTION)
    def _on_uncaught_exception(event: Event):
        logger.error("未捕获的异常\n")
        logger.error(f"类型: {event.data['exc_type']}\n")
        logger.error(f"值: {event.data['exc_value']}\n")
        logger.error("回溯:\n")
        logger.error(event.data['trace'])
        notify_dingtalk(
            pingTestcfg,
            f"出现异常!{event.data['exc_value']}。测试退出"
        )

