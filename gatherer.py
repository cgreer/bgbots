'''
############
Game Process
############

Setup:
    - Choose gatherer position

Turn Process:
    - Choice Where to move next player token to?
    - Choice: Want to use cultural?
    - Choice: Which card to flip face up in row/col?
    - Adjudicate row/col effects
        - For cell w/ face-up card in row/col:
            - Spend/Place resources
                - Choice: Place Resource
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
copy()

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

transitions:
    All of them...
'''
from random import choice

from dataclasses import dataclass
from typing import (
    Any,
    Callable,
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


@dataclass
class Choice:
    choice: str
    on_choice: Tuple[Callable, Any] # fxn, arg1, arg2, ...

    def copy(self):
        return Choice(
            self.choice,
            self.on_choice
        )


STARTING_RES = 5
MAX_RES = 999


@dataclass
class CulturalCard:
    title: str
    cost: str
    ability_idx: int


IsSpend = int # 0:spend, 1:place
SPEND_EFFECT = 0
PLACE_EFFECT = 1
Amount = int
Resource = int # 0:water, 1:food, 2:energy
Direction = int # up, right, down, left


@dataclass
class EffectCard:
    face_up: bool
    direction: Direction
    row_effect: Tuple[IsSpend, Amount, Resource] # XXX: Change to List[...]
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

    def res_sum(self):
        return self.water + self.food + self.energy


class CommonTrans:

    @staticmethod
    def choose_player_location(state, acting_player, after):
        state.prompt = "Move player {acting_player + 1}"
        state.choices = []
        for location in state.eligible_player_movements(acting_player):
            state.choices.append(Choice(
                f"Location {location}",
                after,
            ))

    @staticmethod
    def choose_gatherer_position(state, after):
        state.prompt = "Choose gatherer position"
        state.choices = []
        for row in range(4):
            for col in range(4):
                state.choices.append(Choice(
                    f"Position: ({row}, {col})",
                    after,
                ))


class SetupTrans:

    @staticmethod
    def setup(state):
        after = (TurnTrans.start_turn, 0)
        state.call(CommonTrans.choose_gatherer_position, after)


class TurnTrans:

    @staticmethod
    def start_turn(state, acting_player):
        after = (TurnTrans.choose_card_flip,)
        state.call(
            TurnTrans.choose_player_location,
            acting_player,
            after,
        )

    @staticmethod
    def end_turn(state):
        next_player = state.next_active_player()
        state.call(TurnTrans.start_turn, next_player)

    @staticmethod
    def choose_card_flip(state):
        state.prompt = "Choose card to flip"
        state.choices = []
        for row, col in eli_card_flips():
            on_choice = (TurnTrans.on_flip_choice, row, col)
            state.choices.append(Choice(
                f"Coordinate: ({row}, {col})",
                on_choice,
            ))

    @staticmethod
    def on_flip_choice(state, row, col):
        state.flip_card(row, col)
        state.call(TurnTrans.adjudicate_effects, 0)

    @staticmethod
    def adjudicate_effects(state):
        state.adj_effects = fup_effects()[::-1] # reverse ordered?
        state.call(TurnTrans.adjudicate_effects_loop)

    @staticmethod
    def adjudicate_effects_loop(state):
        '''
        Go through state.adj_cells until there are no cells left to
        adjudicate.
        '''
        # We're done!
        # - Start moving the gatherer phase
        if not state.adj_effects:
            state.call(TurnTrans.start_gatherer_movement,)
            return

        # Adjudicate next effect
        row, col, effect_num = state.adj_effects.pop()
        cell = state.board[row][col]
        is_spend, amount, res = cell.card.active_effects()[effect_num]
        if is_spend == SPEND_EFFECT:
            state.spend_resources(res, amount)
            state.call(TurnTrans.adjudicate_effects_loop)
        else:
            # place first resource on card
            # Then ask where rest of them should go
            # Inception callback??
            after = (TurnTrans.adjudicate_effects_loop,)
            state.call(TurnTrans.place_n, amount, row, col, res, after)

    @staticmethod
    def place_n(state, n, row, col, res, after):
        '''
        Do snake placement of n resources starting at (row, col).

        Then call :after.
        '''
        state.place_info = dict(left=n, placements=[], after=after)
        state.call(TurnTrans.place_n_loop, row, col, res)

    @staticmethod
    def place_n_loop(state, row, col, res):
        # Place the resource
        state.place_resources(row, col, res, 1)
        state.place_info["left"] -= 1
        state.placements["placements"].append((row, col))

        # Decide what to do next
        # - If that was the last resource...
        #   - Call designated callback
        # - Else keep placing
        #   - Call designated callback
        if state.place_info["left"] <= 0:
            after = state.place_info["after"]
            state.call(*after)
            return
        else:
            vps = valid_placements(state.place_info["placements"])
            state.prompt = "Choose placement"
            state.choices = []
            for row, col in vps:
                after = (TurnTrans.place_n_loop, row, col, res)
                state.choices.append(Choice(
                    f"Position: ({row}, {col})",
                    after,
                ))

    @staticmethod
    def start_gatherer_movement(state):
        move_cells = getmovecells()[::-1]

        # No movements to be had
        if not move_cells:
            state.call(TurnTrans.end_turn)
            return

        # Do movements
        state.move_cells = move_cells
        state.call(TurnTrans.gatherer_movement_loop)

    @staticmethod
    def gatherer_movement_loop(state):
        # Move gatherer
        cell = state.move_cells.pop()
        direction = cell.card.direction
        row, col = state.move_gatherer(direction) # XXX check takes direction

        # If last movement
        # - Pick up all
        # - Start next turn
        if not state.move_cells:
            state.pick_up_all(row, col)
            state.call(TurnTrans.end_turn)
            return

        # No res on cell, keep on moving
        cell = state.board[row][col]
        res_choices = cell.res_choices()
        if not res_choices:
            state.call(TurnTrans.gatherer_movement_loop)
            return

        # Res on cell, choose what to pick up
        state.prompt = "Choose resource to pick up"
        state.choices = []
        after = (TurnTrans.gatherer_movement_loop,)
        for res in res_choices:
            state.choices.append(Choice(
                str(res), # XXX: Make pretty
                after,
            ))


Coord = Tuple[int, int] # row, col


@dataclass
class State(BaseState):
    turn_num: int
    acting_player_token: int
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
    choices: List[Choice]

    def call(self, *args):
        '''
        Call a state modifying function

        This state (self) is injected as first argument in call. State
        objects should never be passed in with :args.

        args:
          - 0: fxn
          - (1, ...): fxn args
        '''
        return args[0](self, *args[1:])

    def from_state_key(cls, state_key):
        raise NotImplementedError()

    def to_state_key(self):
        raise NotImplementedError()

    def eligible_actions_lazy(self):
        raise NotImplementedError()

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
        return cards

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

        state = State(
            acting_agent=acting_agent,
            turn_num=0,
            acting_player_token=0,
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

        # Do initial transitions
        state.call(SetupTrans.setup)

    def transition(self, state, action) -> State:
        rstate = state.copy()

        # Call the corresponding handler for the choice
        choice = rstate.choices[action]
        rstate.call(*choice.on_choice)
        return rstate

    def parse_action_input(self, input_string):
        '''Used for converting human input to action'''
        raise NotImplementedError()

    def possible_actions(self):
        '''Used for bots that need it'''
        raise NotImplementedError()

    def reward_range(self):
        '''Used for bots that need it'''
        raise NotImplementedError()
