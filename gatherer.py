'''
############
Game Process
############

Setup:
    - Choose gatherer position
    - Choose player token positions

Turn Process:
    - Choice Where to move player token to?
    - Choice: Want to use cultural?
    - Choice: Which card to flip face up in row/col?
    - Adjudicate row/col effects
        - For face-up card in row/col:
            - Spend/Place resources
    - Move the gatherer
        - For face-up card in row/col:
            - Move gatherer in card's direction
            - Pick up resource(s)
                - If it's last movement
                    - pick up all resources
                - Else
                    Choice: resource to pick up
    - Choice: Purchase cultural?

############
Todo
############

helpers:

eligible_player_movements() [DONE]
    see eligible_player_movements()
eligible_cards_flip() [DONE]
    See flippable_coords()
eligible_placements(origin_coords, placed_coords)
    where can you place this next resource?
iter_face_up_cards() [DONE]
    same as eligible_cards_flip()
eligible_pick_ups() [DONE]

effects:
    move_player() [DONE]
    flip_card() [DONE]
    spend_resources() [DONE]
    place_resources() [DONE]
    move_gatherer() [DONE]
    pick_up_one(coord, resource) [DONE]
    pick_up_all(coord) [DONE]

display:
    console display...

'''
from random import choice

from dataclasses import dataclass
from typing import (
    # Any,
    List,
    Tuple,
)
from base_environment import (
    Environment as BaseEnvironment,
    State as BaseState,
)

enu = enumerate


def clamp(low, val, high):
    if val < low:
        return low
    if val > high:
        return high
    return val


def parse_coords(coords: str):
    # :coords ~ (<row>, <col>)
    coords = coords.strip()[1:-1].split(",")
    row = int(coords[0].strip())
    col = int(coords[1].strip())
    return row, col


STARTING_RES = 5
MAX_RES = 999


@dataclass
class CulturalCard:
    title: str
    cost: str
    ability_idx: int


IsSpend = int # 0:spend, 1:place
Amount = int
Resource = int # 0:water, 1:food, 2:energy
Direction = int # up, right, down, left


@dataclass
class EffectCard:
    face_up: bool
    direction: Direction
    row_effect: Tuple[IsSpend, Amount, Resource]
    col_effect: Tuple[IsSpend, Amount, Resource]

    @classmethod
    def build_random(Cls):
        c = EffectCard(
            face_up=False,
            direction=choice(range(4)),
            row_effect=(
                choice(range(1)),
                choice(range(6)),
                choice(range(2)),
            ),
            col_effect=(
                choice(range(1)),
                choice(range(6)),
                choice(range(2)),
            ),
        )
        return c


EFFECT_CARDS = [EffectCard.build_random() for _ in range(16)]


@dataclass
class Cell(BaseState):
    card: EffectCard
    water: int
    food: int
    energy: int


Coord = Tuple[int, int] # row, col


@dataclass
class State(BaseState):
    turn_num: int
    p1_location: int
    p2_location: int
    gatherer_row: int
    gatherer_col: int
    board: List[List[Cell]]
    water: int # XXX: Starting? Discard has finite size?
    food: int
    energy: int

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

    def copy(self):
        pass

    def eligible_player_movements(self, player):
        locations = list(range(8))
        rem_pos = self.p2_location if player == 0 else self.p1_location
        locations.remove(rem_pos)
        return locations

    def iter_cells(self, is_row, coord) -> Tuple[Coord, Cell]:
        if is_row:
            for col, cell in enu(self.board[coord]):
                yield (coord, col), cell
        else:
            for row in range(4):
                yield (row, coord), self.board[row][coord]

    def flippable_coords(self, is_row, coord):
        cards = []
        for coord, cell in self.iter_cells(is_row, coord):
            if cell.card.face_up:
                continue
            cards.append(coord)

    def move_player(self, player, location):
        if player == 0:
            self.p1_location = location
        elif player == 1:
            self.p2_location = location
        else:
            raise KeyError()

    def flip_card(self, row, col):
        self.board[row][col].card.face_up = True

    def spend_resources(self, resource: int, amount):
        if resource == 0:
            self.water = clamp(0, self.water - amount, MAX_RES)
        elif resource == 1:
            self.food = clamp(0, self.food - amount, MAX_RES)
        elif resource == 2:
            self.energy = clamp(0, self.energy - amount, MAX_RES)
        else:
            raise KeyError()

    def place_resources(self, row: int, col: int, resource: int, amount: int):
        cell = self.board[row][col]
        if resource == 0:
            cell.water = clamp(0, self.water - amount, MAX_RES)
        elif resource == 1:
            cell.food = clamp(0, self.food - amount, MAX_RES)
        elif resource == 2:
            cell.energy = clamp(0, self.energy - amount, MAX_RES)
        else:
            raise KeyError()

    def gain_resources(self, resource: int, amount: int):
        if resource == 0:
            self.water = clamp(0, self.water - amount, MAX_RES)
        elif resource == 1:
            self.food = clamp(0, self.food - amount, MAX_RES)
        elif resource == 2:
            self.energy = clamp(0, self.energy - amount, MAX_RES)
        else:
            raise KeyError()

    def move_gatherer(self, row, col):
        self.gatherer_row = row
        self.gatherer_col = col

    def eligible_pick_ups(self, row, col):
        '''
        Which resources can be picked up here?
        '''
        cell = self.board[row][col]
        res = []
        if cell.water > 0:
            res.append(0)
        if cell.food > 0:
            res.append(1)
        if cell.energy > 0:
            res.append(2)
        return res

    def pick_up_one(self, row, col, resource):
        cell = self.board[row][col]
        if resource == 0:
            if cell.water <= 0:
                raise RuntimeError("How?")
            cell.water = self.water - 1
            self.gain_resources(resource, 1)
        elif resource == 1:
            if cell.food <= 0:
                raise RuntimeError("How?")
            cell.food = self.food - 1
            self.gain_resources(resource, 1)
        elif resource == 2:
            if cell.energy <= 0:
                raise RuntimeError("How?")
            cell.energy = self.energy - 1
            self.gain_resources(resource, 1)
        else:
            raise KeyError()

    def pick_up_all(self, row, col):
        cell = self.board[row][col]
        if cell.water >= 0:
            self.gain_resources(0, cell.water)
            cell.water = 0

        if cell.food >= 0:
            self.gain_resources(1, cell.food)
            cell.food = 0

        if cell.energy >= 0:
            self.gain_resources(2, cell.energy)
            cell.energy = 0

    def is_resource_exhausted(self):
        return (self.water <= 0) or (self.food <= 0) or (self.energy <= 0)

    def is_terminal_lazy(self) -> bool:
        if self.is_resource_exhausted():
            return True
        if self.turn_num == 12: # Reads: "On the start of 13th turn"
            return True

    def to_display_string(self, rich=True) -> str:
        pass

    def choice_display_str(self, action):
        return f"  Player chose: {action}"

    def ui_state(self):
        pass

    def rewards(self):
        if not self.is_terminal():
            return [0.0]
        if sum(self.water, self.food, self.energy) > 10:
            return [1.0]
        else:
            return [-1.0]


class Choices:

    @staticmethod
    def player_location(state, player, setup):
        state.prompt = "Choose player location"
        state.phase = state.phase # nothing changes
        state.subphase = "place_p1"
        state.choices = state.player_loc_choices(player=1)


@dataclass
class Environment(BaseEnvironment):
    NAME = "Gatherer"
    STATE = State

    def initial_state(self):
        acting_agent = 0
        p1_location = 0
        p2_location = 4
        gatherer_row = 0
        gatherer_col = 0
        board = []
        for _ in range(4):
            row = []
            for _ in range(4):
                card = choice(EFFECT_CARDS)
                cell = Cell(card=card, water=0, food=0, energy=0)
                row.append(cell)
            board.append(row)

        # Initial choice...
        prompt = "Choose gatherer location"
        phase = "setup"
        subphase = "place_gatherer"
        choices = []
        for row in range(4):
            for col in range(4):
                choices.append(f"({row}, {col})")

        return State(
            acting_agent=acting_agent,
            p1_location=p1_location,
            p2_location=p2_location,
            gatherer_row=gatherer_row,
            gatherer_col=gatherer_col,
            board=board,
            water=STARTING_RES,
            food=STARTING_RES,
            energy=STARTING_RES,
            prompt=prompt,
            choices=choices,
            phase=phase,
            subphase=subphase,
        )

    def transition(self, cstate, action) -> State:
        state = cstate.copy()

        if state.phase == "setup":
            if state.sub_phase == "place_gatherer":
                choice = state.choices[action]
                row, col = parse_coords(choice)
                state.gatherer_row = row
                state.gatherer_col = col

                # Next transition
                state.prompt = "Choose player location"
                state.phase = state.phase # nothing changes
                state.subphase = "place_p1"
                state.choices = state.player_loc_choices(player=1)
            elif state.sub_phase in ("place_p1", "place_p2"):
                location = int(self.choices[action])
                if state.sub_phase == "place_p1":
                    state.p1_location = location
                    state.choices = state.player_loc_choices(player=1)

                    # Next transition
                    state.prompt = state.prompt
                    # state.phase = "player_movement" # nothing changes
                    state.subphase = "place_p2"
                    # state.choices = choices
                else:
                    p2_location = location
                    state.choices = state.player_loc_choices(player=1)

                    # Next transition
                    state.prompt = "Move Player"
                    state.phase = "player_movement" # nothing changes
                    state.subphase = ""
                    # state.choices = choices
            else:
                raise KeyError()

        elif state.phase == "turn":
            pass

        return state



    def parse_action_input(self, input_string):
        '''Used for converting human input to action'''
        raise NotImplementedError()

    def possible_actions(self):
        '''Used for bots that need it'''
        raise NotImplementedError()

    def reward_range(self):
        '''Used for bots that need it'''
        raise NotImplementedError()
