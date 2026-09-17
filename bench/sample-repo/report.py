"""Builds a plain-text summary of a list of readings."""

from stats import mean, spread, variance
from utils.format import fixed


def summarize(readings):
    lines = [
        "count:    %d" % len(readings),
        "mean:     %s" % fixed(mean(readings)),
        "spread:   %s" % fixed(spread(readings)),
    ]
    if len(readings) >= 2:
        lines.append("variance: %s" % fixed(variance(readings)))
    return "\n".join(lines)
