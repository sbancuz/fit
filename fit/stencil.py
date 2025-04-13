from __future__ import annotations

import random

from fit.distribution import Distribution, Uniform
from fit.memory import IntList


class Stencil:
    """
    Class representing a stencil used for generating random patterns with specified distributions.
    """

    """The distribution for the offsets."""
    offset_distribution: Distribution
    """The distribution for selecting patterns."""
    pattern_distribution: Distribution
    """The patterns to use for the stencil."""
    patterns: list[int]
    """The pattern size."""
    pattern_size: int
    """The word size for the stencil."""
    word_size: int

    def __init__(
        self,
        patterns: int | list[int],
        offset_distribution: Distribution = Uniform(0, 0),
        pattern_distribution: Distribution = Uniform(0, 0),
        word_size: int = 32,
    ) -> None:
        self.offset_distribution = offset_distribution
        self.pattern_distribution = pattern_distribution
        self.patterns = [patterns] if isinstance(patterns, int) else patterns
        self.pattern_size = max([pattern.bit_length() for pattern in self.patterns])
        self.word_size = word_size

        assert len(self.patterns) > 0, "At least one pattern must be provided."
        assert len(self.patterns) - 1 == pattern_distribution.length(), (
            "Number of patterns must match chooser length."
        )

    def random(self) -> IntList:
        """
        Function that generates a random pattern based on the stencil's distributions.

        :return: the IntList representing the random pattern.
        """

        pattern = self.patterns[self.pattern_distribution.random()]
        val = pattern << self.offset_distribution.random()

        max_value = (1 << self.word_size) - 1
        max_number_of_chunks = (max_value.bit_length() + self.word_size - 1) // self.word_size

        res = [0 for _ in range(max_number_of_chunks)]
        for i in range(max_number_of_chunks):
            res[i] = (val >> (self.word_size * i)) & max_value

        return IntList(res)

    def layer(self, max_times: int, min_times: int = 0) -> IntList:
        """
        Function that generates a layered pattern by applying the stencil multiple times.

        :param max_times: the maximum number of times to apply the stencil.
        :param min_times: the minimum number of times to apply the stencil.
        :return: theIntList representing the layered pattern.
        """

        assert min_times <= max_times, "Minimum times must be less than maximum times."

        max_value = (1 << self.word_size) - 1
        max_number_of_chunks = (max_value.bit_length() + self.word_size - 1) // self.word_size
        res = [0 for _ in range(max_number_of_chunks)]

        for _ in range(random.randint(min_times, max_times)):
            choice = self.random()

            for i in range(len(res)):
                res[i] ^= choice[i]

        return IntList(res)
