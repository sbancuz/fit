import random
from abc import ABC, abstractmethod


class Distribution(ABC):
    start_bit = 0
    end_bit = 0
    granularity = 1

    def __init__(self, start_bit: int, end_bit: int, granularity: int = 1) -> None:
        self.start_bit = start_bit
        self.end_bit = end_bit
        self.granularity = granularity

    def length(self) -> int:
        return self.end_bit - self.start_bit

    def adjust(self, value: int) -> int:
        return (value // self.granularity) * self.granularity

    @abstractmethod
    def random(self) -> int: ...

    """
        Returns the bit position for the stencil pattern.
    """


class Uniform(Distribution):
    def random(self) -> int:
        return self.adjust(random.randint(self.start_bit, self.end_bit))


class Normal(Distribution):
    mean: float
    variance: float

    def __init__(self, mean: float, variance: float, granularity: int = 1) -> None:
        self.mean = mean
        self.variance = variance

        self.granularity = granularity
        self.start_bit = int(mean - variance / 2)
        self.end_bit = int(mean + variance / 2)

    def random(self) -> int:
        return self.adjust(int(random.gauss(self.mean, self.variance)))


class Fixed(Distribution):
    cases: list[float]

    def __init__(self, cases: list[float]) -> None:
        assert 1 - sum(cases) <= 1e-6, "Probabilities must sum to 1."

        self.cases = cases
        self.start_bit = 0
        self.end_bit = len(cases) - 1

    def random(self) -> int:
        return random.choices(range(len(self.cases)), weights=self.cases)[0]
