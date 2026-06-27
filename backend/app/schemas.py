from pydantic import BaseModel, Field


class AnalysisOptions(BaseModel):
    lottery_type_2d: str = Field(default="lower2")
    lottery_type_3d: str = Field(default="all3")
    monte_carlo_n: int = Field(default=100000, ge=1000, le=1000000)
    decay_lambda: float = Field(default=0.98, gt=0, lt=1)
    random_seed: int = Field(default=42)


class WeightOptions(BaseModel):
    frequency: float = 0.20
    bayesian: float = 0.20
    markov: float = 0.20
    cycle: float = 0.15
    recency: float = 0.15
    monte_carlo: float = 0.10


class BacktestRequest(BaseModel):
    top_n: list[int] = Field(default_factory=lambda: [3, 5, 10, 20])
    lottery_type_2d: str = "lower2"
    start_after: int = Field(default=10, ge=3)


class MonteCarloRequest(BaseModel):
    lottery_type: str = "lower2"
    digit_length: int = Field(default=2, ge=2, le=3)
    simulations: int = Field(default=100000, ge=1000, le=1000000)
    random_seed: int = 42

