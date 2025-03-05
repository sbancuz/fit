from __future__ import annotations

import random
from abc import ABC, abstractmethod

from fit.memory import IntList


class Stencil:
    distribution: Distribution
    pattern: int
    max_size: int

    def __init__(self, distribution: Distribution, pattern: int, max_size: int = 32):
        self.distribution = distribution
        self.pattern = pattern
        self.max_size = max_size

        pattern_size = pattern.bit_length()
        assert 0 <= pattern_size and pattern_size <= max_size
        assert (
            distribution.start_bit <= pattern.bit_length()
            and pattern.bit_length() <= distribution.end_bit
        )

    def random(self) -> int | IntList:
        if self.distribution.start_bit == self.distribution.end_bit:
            return self.distribution.start_bit

        if self.distribution.end_bit - self.distribution.start_bit < self.max_size:
            return self.pattern << self.distribution.random()

        number_of_chunks = self.distribution.length() // self.max_size + 1
        res = [0 for _ in range(number_of_chunks)]

        choice = self.distribution.random()
        res[choice // self.max_size] = self.pattern << (choice % self.max_size)
        if choice % self.max_size + self.pattern.bit_length() > self.max_size:
            res[choice // self.max_size + 1] = self.pattern >> (
                self.max_size - choice % self.max_size
            )

        return res if isinstance(res, int) else IntList(res)

    def layer(self, max_times: int, min_times: int = 0) -> int | IntList:
        assert min_times <= max_times, "Minimum times must be less than maximum times."

        res: int | list[int] = 0
        if not self.distribution.length() < self.max_size:
            res = [0 for _ in range(self.distribution.length() // self.max_size + 1)]

        for _ in range(random.randint(min_times, max_times)):
            ## TODO: Maybe use or instead of xor
            choice = self.random()

            if isinstance(res, int):
                assert isinstance(choice, int)

                res ^= choice
            else:
                assert isinstance(choice, list)
                for i in range(len(res)):
                    res[i] ^= choice[i]

        return res if isinstance(res, int) else IntList(res)


class Distribution(ABC):
    start_bit = 0
    end_bit = 0

    def __init__(self, start_bit: int, end_bit: int) -> None:
        self.start_bit = start_bit
        self.end_bit = end_bit

    def length(self) -> int:
        return self.end_bit - self.start_bit

    @abstractmethod
    def random(self) -> int: ...

    """
        Returns the bit position for the stencil pattern.
    """

    @abstractmethod
    def shrink_bounds(self, pattern_size: int) -> None:
        remove = pattern_size // 2
        leftover = pattern_size % 2

        self.start_bit += remove
        self.end_bit -= remove + leftover


class Uniform(Distribution):
    def random(self) -> int:
        return random.randint(self.start_bit, self.end_bit)


class Normal(Distribution):
    mean: float
    variance: float

    def __init__(self, mean: float, variance: float) -> None:
        self.mean = mean
        self.variance = variance

        self.start_bit = int(mean - variance / 2)
        self.end_bit = int(mean + variance / 2)

    def random(self) -> int:
        return int(random.gauss(self.mean, self.variance))

    def shrink_bounds(self, pattern_size: int) -> None:
        super().shrink_bounds(pattern_size)

        self.variance -= float(pattern_size) / 2
