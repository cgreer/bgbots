from typing import (
    Any,
    Union,
    List,
)

# Basic
Number = Union[int, float]
Instance = Any # Instance of a class
JSONString = str
SecondsSinceEpoch = float


# RL types
EnvironmentType = str
AgentType = str
Agent = Any
Action = int
Value = float
Values = List[float]
Policy = List[float] # could be probability (sum to 1)
Rewards = List[float]
StateKey = str # or tuple?
Outcome = Rewards

# Model specific
Temperature = float

# Performance Evaluation
# - OptimalReward is from the POV of a state's acting agent.
OptimalAction = int
OptimalReward = float
