import random


def safe_randint(low: int, high: int | None = None) -> int:
    if high is None:
        high = low
        low = 0
    return random.randint(low, high)
