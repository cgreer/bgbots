from dataclasses import dataclass
import random
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
        actions = self.environment.current_state().eligible_actions()
        return random.choice(actions)

    def is_client(self):
        return False
