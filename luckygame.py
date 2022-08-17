from random import choice

from dataclasses import dataclass
from typing import (
    # Any,
    List,
)
from base_environment import (
    Environment as BaseEnvironment,
    State as BaseState,
)

enu = enumerate


@dataclass
class State(BaseState):
    boxes: List[int]
    prize: int

    # Choice info for UI
    prompt: str
    choices: List[str]

    def from_state_key(cls, state_key):
        raise NotImplementedError()

    def to_state_key(self):
        raise NotImplementedError()

    def eligible_actions_lazy(self):
        # choices are ~ ["0", "2", ...]
        return [int(x) for x in self.choices]

    def winner(self):
        winner = None
        if self.boxes[self.prize] != 0:
            winner = self.boxes[self.prize - 1]
        return winner

    def is_terminal_lazy(self) -> bool:
        '''
        Method that is called the first time is_terminal is called
        and result cached.

        Don't call this method directly, use is_terminal.
        '''
        if self.winner() is None:
            return False
        return True

    def to_display_string(self, rich=True) -> str:
        s = ""
        s += "\nBox states: " + str(self.boxes)
        s += "\nChoices: " + str(self.choices)
        s += "\nPrice Position: " + str(self.prize)
        return s

    def choice_display_str(self, action):
        return f"  Player chose: {action}"

    def ui_state(self):
        winner = self.winner()
        return dict(
            boxes=self.boxes[:],
            winner=winner,
        )

    def rewards(self):
        if self.winner() is None:
            return [0.0, 0.0]

        r = [-1.0, -1.0]
        r[self.winner() - 1] = 1.0
        return r


@dataclass
class Environment(BaseEnvironment):
    NAME = "Lucky"
    STATE = State

    def initial_state(self):
        acting_agent = choice(range(2))
        boxes = [0] * 5
        prize = choice(range(5))
        choices = [str(i) for i in range(5)]
        return State(
            acting_agent=acting_agent,
            boxes=boxes,
            prize=prize,
            prompt="Choose box",
            choices=choices,
        )

    def transition(self, state, action) -> State:
        # Build next state
        acting_agent = 1 if state.acting_agent == 0 else 0
        boxes = state.boxes[:] # Copy the previous boxes

        # Player chose action x which corresponds to index x in boxes,
        # and add 1 to make it "player 1" instead of "Player 0"
        # [0, 0, 0]
        # [0, 1, 0]
        boxes[action] = state.acting_agent + 1

        # Build the UI choices
        choices = []
        for i, bstate in enumerate(boxes):
            if bstate == 0:
                choices.append(str(i))

        return State(
            acting_agent=acting_agent,
            boxes=boxes,
            prize=state.prize,
            prompt=state.prompt,
            choices=choices,
        )

    def parse_action_input(self, input_string):
        '''Used for converting human input to action'''
        raise NotImplementedError()

    def possible_actions(self):
        '''Used for bots that need it'''
        raise NotImplementedError()

    def reward_range(self):
        '''Used for bots that need it'''
        raise NotImplementedError()
