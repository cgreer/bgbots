from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    Any,
)

from custom_types import (
    EnvironmentType
)
from run_contexts import RunContexts

Action = Any


@dataclass
class Agent(ABC):
    environment: Any = field(init=False)
    agent_num: int = field(init=False)

    @classmethod
    def build(cls, *args, **kwargs):
        # Capture this way to enforce passing in kwargs
        settings = kwargs.get("settings")
        env_type = kwargs.get("env_type")
        run_context = kwargs.get("run_context")

        # Either provide settings or (env_type, run_context)
        if settings is not None:
            assert env_type is None
            assert run_context is None
        else:
            assert settings is None
            settings = cls.build_settings(env_type, run_context)
        return cls(**settings)

    @classmethod
    def build_settings(
        cls,
        env_type: EnvironmentType,
        run_context: RunContexts,
        version: int = None,
    ):
        return {}

    def set_agent_num(self, agent_num):
        self.agent_num = agent_num

    @abstractmethod
    def set_up(self, **kwargs):
        pass

    @abstractmethod
    def handle_event(self, event):
        pass

    @abstractmethod
    def select_action(self) -> Action:
        pass

    @abstractmethod
    def is_client(self) -> bool:
        '''
        Does this agent represent a human client that submits moves to
        a game server?
        '''
        pass
