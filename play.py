import math
from timing import report_every

from settings import SETTINGS
from random_agent import Agent as RandomAgent
from luckygame import Environment as LuckyGame


def play(Game):
    # Pick agents
    agents = [
        RandomAgent.build(),
        RandomAgent.build(),
    ]

    # Pick game/seed
    game = LuckyGame()
    game.initialize(
        agents,
        seed=None, # None will create rand seed
    )
    game.run() # run game on CLI


def random_win_rate(Game, N=1000):
    agents = [
        RandomAgent.build(),
        RandomAgent.build(),
    ]
    SETTINGS.disable_output()
    p1_wins = 0
    for _ in range(N):
        report_every("Games played", 1000)
        game = Game()
        game.initialize(
            agents,
            seed=None, # None will create rand seed
        )
        game.run() # run game on CLI
        winner = game.current_state().winner()
        if winner == 0:
            p1_wins += 1

    p = p1_wins / N
    p1_wins_std = math.sqrt(N * p * (1 - p)) # Binomial distribution
    error = p1_wins_std / N

    print("\nResults")
    print(f"  P1 games won: {p1_wins} / {N}")
    print(f"  +/-: {round(p1_wins_std, 1)}")
    print()
    print(f"  P1 win rate: {round(p, 2)}")
    print(f"  +/-: {round(error, 4)}")
    print()


if __name__ == "__main__":
    play(LuckyGame)
    random_win_rate(LuckyGame, 10_000)
