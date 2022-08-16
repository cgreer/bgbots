from dataclasses import dataclass
from typing import ClassVar

from base_agent import Agent as BaseAgent

Action = int


@dataclass
class Agent(BaseAgent):
    NAME: ClassVar[str] = "random"

    def set_up(self, **kwargs):
        pass

    def handle_event(self, event):
        pass

    def select_action(self) -> Action:
        raise RuntimeError("Remote agents should never select actions")

    def is_client(self):
        return True
