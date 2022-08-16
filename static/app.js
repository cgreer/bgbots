function clamp(low, value, high) {
  if (value < low) {
    return low;
  }
  if (value > high) {
    return high
  }
    return value;
}

function setRequired(obj, attr, value) {
  if (value == null) {
   throw new Error(`attr is required: ${attr}`);
  }

  obj[attr] = value;
}

class Component {

  constructor() {
    this.rootContainerId = null;
  }

  rootElement() {
    return document.getElementById(this.rootContainerId);
  }

  spawn(containerId) {

    // Set rootContainerId
    this.rootContainerId = containerId

    // Replace/add html to container
    document.getElementById(containerId).innerHTML = this.buildHtml();

    this.afterBuildHtml()

    // Link/stash references to objects
    this.buildRefs();

    // Create any event handlers
    this.buildEventHandlers();

    return this;
  }

  afterBuildHtml() {}

  buildHtml() {
     throw new Error("Method must be implemented.");
  }

  buildRefs() {}

  buildEventHandlers() {}

  bindRefCss(varName, cssPath) {
    // Helper method to help bind references:
    //
    // Usage:
    //   this.bindRefCss("addButton", ".dayplan .disheslist .adddish");
    let rootElString = "#" + this.rootContainerId;
    let el = document.querySelector(rootElString + " " + cssPath);
    this[varName] = el;
    console.assert(this[varName] != null);
  }

}

class Board extends Component {

  constructor(boardState) {
    super();

    setRequired(this, "boardState", boardState);

    // Boxes
    // 0 - picked
    // 1 - P1 picked (not prize)
    // 2 - P1 picked (not prize)
    // 3 - Prize
    // this.boxes = [0, 0, 0, 1, 0];
  }

  buildHtml() {
    var boardInner = ''
    this.boardState.boxes.forEach((el, idx, arr) => {
      if (el === 0) {
        boardInner += `? `;
      } else if (el === 1 || el === 2) {
        boardInner += `${el} `;
      }
      else {
        boardInner += `! `;
      }
    })

    var html = `
        <div>${boardInner}</div>
    `;
    return html;
  }

  afterBuildHtml() {}
}

class ActionSelectionArea extends Component {

  constructor(promptText, choices, onChoices) {
    super();
    setRequired(this, "promptText", promptText);
    setRequired(this, "choices", choices);
    setRequired(this, "onChoices", onChoices);
  }

  buildHtml() {
    var actionHtml = ''
    this.choices.forEach((el, idx, arr) => {
      actionHtml += `\n<div class="action">${el}</div>`;
    })

    var html = `
      <div class="inputarea flex-col-st-ce">

        <div class="prompt">
          ${this.promptText}
        </div>

        ${actionHtml}
      </div>
    `;
    return html;
  }

  afterBuildHtml() {
    // Bind onChoices to action buttons
    let els = document.querySelectorAll(".inputarea .action");
    els.forEach((el, idx) => {
      el.addEventListener(
        'click',
        (event) => {this.onChoices[idx](event)}
      )
    });
  }

}

class InputAreaView extends Component {

  constructor(app) {
    super();

    setRequired(this, "app", app);

    // Data
    this.promptText = "Choices";
    this.choices = [
        "Start New Game",
        "Game Updates",
        "Submit Action (1)",
        "Submit Action (2)",
        "Submit Action (3)",
        "Submit Action (4)",
        "Submit Action (5)",
    ];
    this.onChoices = [
      (event) => {this.onNewGame(event)},
      (event) => {this.onGetUpdates(event)},
      (event) => {this.onSubmitAction(event, 0)},
      (event) => {this.onSubmitAction(event, 1)},
      (event) => {this.onSubmitAction(event, 2)},
      (event) => {this.onSubmitAction(event, 3)},
      (event) => {this.onSubmitAction(event, 4)},
    ]
  }

  onNewGame(event) {
    fetch('/new_game')
    .then((response) => response.json())
    .then((data) => {
      this.app.gameId = data.gameId
      console.log("stashed game id: ", data.gameId)
    });
  }

  onGetUpdates(event) {
    fetch(
      '/game_updates',
      {
        method: "POST",
        body: JSON.stringify({
          "gameId": APP.gameId,
        })
      }
    )
    .then((response) => response.json())
    .then((data) => {
      console.log("response", data);
      this.app.gameHistory = data.gameHistory;
      this.app.update();
    });
  }

  onSubmitAction(event, action) {
    fetch(
      '/submit_action',
      {
        method: "POST",
        body: JSON.stringify({
          "gameId": APP.gameId,
          "action": action,
        })
      }
    )
    .then((response) => response.json())
    .then((data) => {
      console.log("response", data);
    });
  }

  updateView() {
    new ActionSelectionArea(
      this.promptText,
      this.choices,
      this.onChoices,
    ).spawn("actionselection");
  }

  buildHtml() {
    return `<div id="actionselection"></div>`
  }

  afterBuildHtml() {
    this.updateView()
  }

}


class App extends Component {

  constructor(entityData) {
    super();

    // setRequired(this, "entityData", entityData);

    // App Data
    this.activeMainView = null;
    this.activeModalView = null;

    // Views
    this.inputAreaView = null;

    // EntityData
    // this.data = entityData
    this.gameId = null;
    this.gameHistory = [];
    this.defaultBoardState = {
      "boxes": [0, 0, 0, 0, 0],
    }
  }

  setActiveView(view) {
    view.rootElement().classList.remove("hidden");
    if (this.activeMainView != null) {
      this.activeMainView.rootElement().classList.add("hidden");
    }
    this.activeMainView = view;
  }

  showView(view) {
    view.loadView();
    this.setActiveView(view);
  }

  buildHtml() {
    var html = `
      <div class="ui-cont flex-row-st-ce">
        <div class="board-cont flex-col-ce-ce">
          <div id="board" class="board"></div>
        </div>
        <div class="input-cont">
          <div id="inputarea"></div>
        </div>
      </div>
    `;
    return html;
  }

  afterBuildHtml() {
    // Load subcomponents
    this.inputAreaView = new InputAreaView(this).spawn("inputarea");
    this.update();
  }

  update() {
    // Get current board state (or default)
    var boardState = this.defaultBoardState;
    if (this.gameHistory.length > 0) {
      boardState = this.gameHistory[this.gameHistory.length - 1];
    }
    new Board(boardState).spawn("board");
  }
}
