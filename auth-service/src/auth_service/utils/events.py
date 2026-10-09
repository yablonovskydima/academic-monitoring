from auth_shared import AuthEvent


def publish_event(event: AuthEvent, payload: dict) -> None:
    print(f"[event] {event.value} {payload}")
