"""
Module containing low-level math utilities used by iter8
"""

# core python dependencies
import math
from random import random

# round a sequence of weights into a sequence of integer weights so that they sum up to Math.floor(total)
# further, rounded values equal the original values in expectation
# assumption: all inputs are non-negative
def gen_round(weights, total):  # generator
    # initialize the generator
    total = math.floor(total)

    #  randomized rounding of a
    def fix(a): return math.ceil(a) if random() < a - math.floor(a) else math.floor(a)

    # renormalize weights
    def normalize(weights):
        if sum(weights) == 0:
            weights = [1 for x in weights]  # weights summing up now to a value > 0
        weightSum = sum(weights)
        return [x*total / weightSum for x in weights]

    # yield rounded values iteratively
    while len(weights):
        fixed = fix(normalize(weights)[0])
        yield fixed
        weights, total = weights[1:], total - fixed
