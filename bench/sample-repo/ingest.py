"""Reads readings from a text file, one number per line, and drops outliers."""

from stats import mean


def load(path):
    with open(path, encoding="utf-8") as f:
        return [float(line) for line in f if line.strip()]


def drop_outliers(readings, factor=3.0):
    """Keep readings within `factor` times the mean absolute deviation of the mean."""
    centre = mean(readings)
    deviation = mean([abs(r - centre) for r in readings]) or 1.0
    return [r for r in readings if abs(r - centre) <= factor * deviation]
