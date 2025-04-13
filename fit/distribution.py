import random
from abc import ABC, abstractmethod


class Distribution(ABC):
    """
    Abstract base class for defining different types of distributions.
    """

    """The starting bit position."""
    start_bit = 0
    """The ending bit position."""
    end_bit = 0
    """The granularity of adjustment for the values. Default is 1."""
    granularity = 1

    def __init__(self, start_bit: int, end_bit: int, granularity: int = 1) -> None:
        self.start_bit = start_bit
        self.end_bit = end_bit
        self.granularity = granularity

    def length(self) -> int:
        """
        Function that computes the length of the distribution.

        :return: the length of the distribution.
        """

        return self.end_bit - self.start_bit

    def adjust(self, value: int) -> int:
        """
        Function that adjusts the value to the nearest multiple of the granularity.

        :param value: the value to be adjusted.
        :return: the adjusted value.
        """

        return (value // self.granularity) * self.granularity

    @abstractmethod
    def random(self) -> int: ...

    """
    Abstract method that generates a random value based on the distribution.

    :return: the random value.
    """


class Uniform(Distribution):
    """
    Uniform distribution class that generates random values based on the uniform distribution.
    """

    def random(self) -> int:
        """
        Function that generates a random values based on the uniform distribution.

        :return: the random value.
        """

        return self.adjust(random.randint(self.start_bit, self.end_bit))


class Normal(Distribution):
    """
    Normal distribution class that generates random values based on the normal distribution.
    """

    """The mean of the normal distribution."""
    mean: float
    """The variance of the normal distribution."""
    variance: float

    def __init__(self, mean: float, variance: float, granularity: int = 1) -> None:
        self.mean = mean
        self.variance = variance

        self.granularity = granularity
        self.start_bit = int(mean - variance / 2)
        self.end_bit = int(mean + variance / 2)

    def random(self) -> int:
        """
        Function that generates a random values based on the normal distribution.

        :return: the random value.
        """

        return self.adjust(int(random.gauss(self.mean, self.variance)))


class Fixed(Distribution):
    """
    Fixed distribution class that generates random values based on the fixed distribution.
    """

    """The list of probabilities for each case. The probabilities must sum to 1."""
    cases: list[float]

    def __init__(self, cases: list[float]) -> None:
        assert 1 - sum(cases) <= 1e-6, "Probabilities must sum to 1."

        self.cases = cases
        self.start_bit = 0
        self.end_bit = len(cases) - 1

    def random(self) -> int:
        """
        Function that generates a random values based on the fixed distribution.

        :return: the random value.
        """

        return random.choices(range(len(self.cases)), weights=self.cases)[0]
