"""Synchronous in-process event bus."""

from collections import defaultdict
from collections.abc import Callable
from typing import Any

Subscriber = Callable[[dict[str, Any]], None]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: defaultdict[str, list[Subscriber]] = defaultdict(list)

    def subscribe(self, topic: str, subscriber: Subscriber) -> None:
        self._subscribers[topic].append(subscriber)

    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        for subscriber in list(self._subscribers.get(topic, [])):
            subscriber(payload)


event_bus = EventBus()
