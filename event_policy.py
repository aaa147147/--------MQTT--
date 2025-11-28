from event_manager import EventType

VALID_ACTIONS = {"exit", "restart", "ignore"}

def _normalize(action):
    if not isinstance(action, str):
        return None
    a = action.strip().lower()
    return a if a in VALID_ACTIONS else None

def resolve_event_action(cfg, event_type: EventType, default: str = "exit"):
    mapping = getattr(cfg, "EVENT_ACTIONS", {}) or {}
    val = None
    key = event_type.name
    if isinstance(mapping, dict):
        val = mapping.get(key)
    action = _normalize(val) or _normalize(default) or "exit"
    return action

def should_restart(cfg, event_type: EventType):
    return resolve_event_action(cfg, event_type) == "restart"

