from math import floor, ceil


def to_refined(scrap: int) -> float:
    """returns refined value given scrap value
    ex: 174 -> 19.33"""
    return floor(scrap / 9 * 100) / 100


def to_scrap(refined: float) -> int:
    """returns scrap value given refined value
    ex: 19.33 -> 174"""
    return ceil(refined * 9)


def refinedify(value: float) -> float:
    """turn wrong ref value into a correct one
    ex: 18.63 -> 18.66"""
    return (
        floor((round(value * 9, 0) * 100) / 9) / 100
        if value > 0
        else ceil((round(value * 9, 0) * 100) / 9) / 100
    )
