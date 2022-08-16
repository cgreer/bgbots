from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict, field
import json
from typing import (
    # Any,
    ClassVar,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
)
import random
import time
import uuid
import numpy

from rich import print as rprint

from settings import SETTINGS
from custom_types import (
    Action,
    Agent,
    Instance,
    JSONString,
    Outcome,
    Rewards,
    SecondsSinceEpoch,
    StateKey,
)


@dataclass
class State(ABC):
    acting_agent: int

    _cached_is_terminal: Optional[bool] = field(init=False, default=None)
    _cached_eligible_actions: Optional[List[Action]] = field(init=False, default=None)

    @classmethod
    def from_dict(cls, data: Dict) -> Instance:
        return cls(**data)

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_json(self) -> JSONString:
        return json.dumps(self.to_dict())

    def is_terminal(self):
        # Lazily set
        if self._cached_is_terminal is None:
            self._cached_is_terminal = self.is_terminal_lazy()
        return self._cached_is_terminal

    def eligible_actions(self) -> Iterable[Action]:
        # Lazily set
        if self._cached_eligible_actions is None:
            self._cached_eligible_actions = self.eligible_actions_lazy()
        return self._cached_eligible_actions

    @classmethod
    @abstractmethod
    def from_state_key(cls, state_key) -> Instance:
        pass

    @abstractmethod
    def to_state_key(self) -> StateKey:
        pass

    @abstractmethod
    def eligible_actions_lazy(self) -> Iterable[Action]:
        pass

    @abstractmethod
    def is_terminal_lazy(self) -> bool:
        '''
        Method that is called the first time is_terminal is called
        and result cached.

        Don't call this method directly, use is_terminal.
        '''
        pass

    @abstractmethod
    def rewards(self) -> List[float]:
        '''
        Rewards that each agent gets from this state.

        Typically called only when the state is terminal for board
        games, but that's not strictly true.
        '''
        pass

    @abstractmethod
    def to_display_string(self, rich=True) -> str:
        pass


@dataclass
class Event:
    action: Action
    rewards: Rewards
    state: State

    @classmethod
    def from_dict(cls, data, State):
        state_key = data["state"]
        data["state"] = State.from_state_key(state_key)
        return cls(**data)

    def to_dict(self):
        return {
            "action": self.action,
            "rewards": self.rewards,
            "state": self.state.to_state_key(),
        }


@dataclass
class Environment(ABC):
    NAME: ClassVar[str] = None
    STATE: ClassVar[str] = None

    id: str = field(init=False)
    agents: List[Agent] = field(init=False)
    event_history: List[Event] = field(init=False)
    start_time: SecondsSinceEpoch = field(init=False)
    end_time: SecondsSinceEpoch = field(init=False)
    random_seed: int = field(init=False)

    def __post_init__(self):
        self.id = str(uuid.uuid4())
        self.event_history = []
        self.agents = []
        self.start_time = -1.0
        self.end_time = -1.0
        self.random_seed = None
        assert self.NAME
        assert self.STATE

    def initialize(self, agents, seed=None):
        # Initialize environment
        self.set_seed(seed=seed) # Random seed
        for agent in agents:
            self.add_agent(agent)
        self.set_up()

    def set_seed(self, seed=None):
        if seed is None:
            self.random_seed = random.randint(0, 100_000_000)
        else:
            self.random_seed = seed
        random.seed(self.random_seed)
        numpy.random.seed(self.random_seed)

    def add_agent(self, agent):
        self.agents.append(agent)
        agent.set_agent_num(len(self.agents) - 1)
        agent.environment = self

    def num_agents(self) -> int:
        return len(self.agents)

    def acting_agent(self) -> Agent:
        return self.agents[self.current_state().acting_agent]

    def get_name(self) -> str:
        return self.NAME

    def action_number(self):
        '''
        1-based
        '''
        event_history = self.event_history
        return len(event_history)

    def current_state(self):
        return self.event_history[-1].state

    def to_display_string(self, terminal=False):
        current_state = self.current_state()
        if terminal:
            header_text = "GAME OVER"
        else:
            action_number = self.action_number()
            player = current_state.acting_agent + 1
            header_text = f" ACTION {action_number} (P{player})"
        state_display_string = current_state.to_display_string()
        display_string = f"\n\n====== {header_text} ======"
        display_string += f"\n\n{state_display_string}"
        return display_string

    def display(self, terminal=False):
        rprint(self.to_display_string(terminal=terminal))

    def display_setup(self):
        to_display_string = f"\nEnvironment: {self.NAME}"
        for i, agent in enumerate(self.agents):
            to_display_string += f"\nAgent {i}: {agent.NAME}"
        to_display_string += f"\nRandom seed: {self.random_seed}"
        rprint(to_display_string)

    def set_up(self, replay_history=None):
        replay_history = replay_history if replay_history else []

        # Make sure things that need to be set are set.
        assert self.id
        assert self.agents
        assert self.random_seed

        # Set up environment with initial state and let agents set up.
        if replay_history:
            initial_event = replay_history.pop(0)
        else:
            initial_event = Event(
                action=None,
                rewards=None,
                state=self.initial_state(),
            )
        self.event_history.append(initial_event)
        for agent in self.agents:
            agent.set_up()

        # Replay environment until last event
        while replay_history:
            event = replay_history.pop(0)
            self.event_history.append(event)

            # - XXX: mask unobservable state here.
            for agent in self.agents:
                agent.handle_event(event)

    def advance(self, action):
        '''
        Transition the environment from state_n to state_n+1 given an
        :action.

        Unlike :transition, this method advances the environment
        by updating the game history and handling any logic (like
        alerting agents to moves) that needs doing.

        :transition can be called at any time to get the state the
        environment would advance to if the action was executed.
        '''
        # Advance game state
        # - Inform agents about event so they can do any work
        #   needed.
        state = self.current_state()
        next_state = self.transition(
            state,
            action,
        )
        event = Event(
            action=action,
            rewards=next_state.rewards(),
            state=next_state,
        )
        self.event_history.append(event)
        for agent in self.agents:
            agent.handle_event(event)
        # print("advance", state.acting_agent, "action", action)

    def run(self) -> Outcome:
        '''
        Run environment locally (command line or headless)

        If a there are human agents then actions will be elicited from
        them on the terminal.
        '''
        event_history = self.event_history
        display = self.display
        agents = self.agents

        # Display Setup
        if SETTINGS.display_environment_state:
            self.display_setup()

        # Run
        self.start_time = time.time()
        while True:
            current_state = self.current_state()

            # Stop if game is over
            if current_state.is_terminal():
                if SETTINGS.display_environment_state:
                    display(terminal=True)
                break

            if SETTINGS.display_environment_state:
                display()

            # Get next action from agent
            agent_to_choose = agents[current_state.acting_agent]
            chosen_action_id = agent_to_choose.select_action()

            if SETTINGS.display_environment_state:
                print(current_state.choice_display_str(chosen_action_id))

            # Advance game state
            self.advance(chosen_action_id)
        self.end_time = time.time()

        return event_history[-1].rewards

    def run_hosted(self):
        '''
        Run environment until:
        - It is a human player's turn
        - The game is over
        '''
        # Run
        while True:
            state = self.current_state()

            # Stop if game is over
            if state.is_terminal():
                print("Game over")
                break

            # Stop if a client (i.e., human) needs to choose an action
            acting_agent = self.agents[state.acting_agent]
            if acting_agent.is_client():
                break

            # Advance game state
            action = acting_agent.select_action()
            self.advance(action)
        return

    @abstractmethod
    def initial_state(self) -> State:
        pass

    @abstractmethod
    def transition(self, state, action) -> State:
        '''
        simulate and return the next state given a state and an
        action.
        '''
        pass

    @abstractmethod
    def parse_action_input(self, input_string) -> Action:
        pass

    @abstractmethod
    def possible_actions(self) -> Iterable[Action]:
        '''
        Set of actions that are possible to execute in this
        environment. This IS not the actions for a given state, but
        for the entire environment.
        '''
        pass

    @abstractmethod
    def reward_range(self) -> Tuple[float, float]:
        '''
        What's the inclusive [low, high] range that a reward can be.
        Used to clip value estimate predictions when they are too
        high/low.
        '''
        pass
