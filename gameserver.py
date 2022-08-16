from uuid import uuid4
from typing import (
    Any,
    Dict,
)
from flask import (
    Flask,
    Response,
    request,
    jsonify,
)

from random_agent import Agent as RandomAgent
from client_agent import Agent as ClientAgent
from luckygame import Environment as LuckyGame

app = Flask(__name__)


ACTIVE_GAMES: Dict[str, Any] = {}# guid, environment


@app.route("/new_game")
def new_game():

    # Start a new game
    # - Advance it until it's a client's turn to act.
    agents = [
        ClientAgent.build(),
        RandomAgent.build(),
    ]
    env = LuckyGame()
    env.initialize(agents)
    env.run_hosted()

    game_id = str(uuid4())
    ACTIVE_GAMES[game_id] = env

    data = {"gameId": game_id}
    return jsonify(data)


@app.route("/game_updates", methods=["POST"])
def game_updates():
    data = request.get_json(force=True)

    # Lookup game
    game_id = data["gameId"]
    env = ACTIVE_GAMES[game_id]

    # Get view information
    gameHistory = []
    for event in env.event_history:
        state = event.state
        gameHistory.append(state.ui_state())

    data = {
        "gameHistory": gameHistory,
    }
    return jsonify(data)


@app.route("/submit_action", methods=["POST"])
def submit_action():
    # Extract data
    data = request.get_json(force=True)
    game_id = data["gameId"]
    action = data["action"]

    # Advance the game
    # - First apply the action to do a transition
    # - Then advance until game needs client action
    env = ACTIVE_GAMES[game_id]
    env.advance(action)
    env.run_hosted()

    data = {
        "success": True,
    }
    return jsonify(data)


@app.route("/<filename>.css")
def static_css(filename):
    body = open(f"./static/{filename}.css", "r").read()
    return Response(body, mimetype="text/css")


@app.route("/<filename>.js")
def static_js(filename):
    body = open(f"./static/{filename}.js", "r").read()
    return Response(body, mimetype="text/javascript")


@app.route("/")
def index():
    response = open("./static/index.html", "r").read()
    return response
