import random
from minigames_gains import get_gains


def loaded_dice():
    gains = get_gains("loaded_dice")
    result = random.randint(1, 6)

    return [result], result, gains[result - 1]


def magic_roll():
    gains = get_gains("magic_roll")

    dices = [random.randint(1, 6) for _ in range(3)]
    result = sum(dices)

    distance_from_edge = min(result - 3, 18 - result)

    gain = gains[distance_from_edge] if distance_from_edge < len(gains) else 0

    return dices, result, gain


def golden_gamble():
    gains = get_gains("golden_gamble")

    dices = [random.randint(1, 6) for _ in range(3)]
    result = sum(dices)

    gain = gains[0] + gains[1] if result in (10, 11, 12) else gains[0]

    return dices, result, gain