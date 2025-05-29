from __future__ import annotations

import random

from fit.distribution import Distribution, Uniform
from fit.memory import IntList


def bits(val: int) -> int:
    if val == 0:
        return 1

    return val.bit_length()


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
    pattern_size_in_words: int
    """The word size for the stencil."""
    word_size: int

    def __init__(
        self,
        patterns: int | list[int],
        offset_distribution: Distribution = Uniform(0, 0),
        pattern_distribution: Distribution = Uniform(0, 0),
        word_size: int = 4,
    ) -> None:
        self.offset_distribution = offset_distribution
        self.pattern_distribution = pattern_distribution
        self.patterns = [patterns] if isinstance(patterns, int) else patterns
        self.bits = word_size * 8
        self.pattern_size = max(
            # Here we want to find the biggest pattern, we subtract one from
            # bits(pattern) since if we have a pattern like 0xffffffff we would have
            # a pattern that would be larger than needed
            [((bits(pattern) - 1) // self.bits) + 1 for pattern in self.patterns]
        )

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

        max_value = (1 << self.bits) - 1
        offlen = (
            self.offset_distribution.length() - 1 if self.offset_distribution.length() > 0 else 1
        )
        max_number_of_chunks = (offlen) // self.bits + (self.pattern_size)

        res = [0 for _ in range(max_number_of_chunks)]
        for i in range(max_number_of_chunks):
            res[i] = (val >> (self.bits * i)) & max_value

        return IntList(res)

    def layer(self, max_times: int, min_times: int = 0) -> IntList:
        """
        Function that generates a layered pattern by applying the stencil multiple times.

        :param max_times: the maximum number of times to apply the stencil.
        :param min_times: the minimum number of times to apply the stencil.
        :return: theIntList representing the layered pattern.
        """

        assert min_times <= max_times, "Minimum times must be less than maximum times."

        max_number_of_chunks = self.offset_distribution.length() // self.bits + (
            self.pattern_size - 1
        )
        res = [0 for _ in range(max_number_of_chunks)]
        for _ in range(random.randint(min_times, max_times)):
            choice = self.random()

            for i in range(len(res)):
                res[i] ^= choice[i]

        return IntList(res)
