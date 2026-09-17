"""Small statistics helpers used by the report and CLI modules."""


def mean(values):
    """Arithmetic mean of a non-empty sequence."""
    if not values:
        raise ValueError("mean() needs at least one value")
    return sum(values) / len(values)


def variance(values):
    """Sample variance (divides by n - 1) of a sequence with at least two values."""
    if len(values) < 2:
        raise ValueError("variance() needs at least two values")
    m = mean(values)
    return sum((v - m) ** 2 for v in values) / (len(values) - 1)


def median(values):
    """Median of a non-empty sequence."""
    if not values:
        raise ValueError("median() needs at least one value")
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def spread(values):
    """Difference between the largest and smallest value."""
    if not values:
        raise ValueError("spread() needs at least one value")
    return max(values) - min(values)
