"""Command line entry point: python cli.py readings.txt"""

import sys

import stats
from ingest import drop_outliers, load
from report import summarize


def main(argv):
    if len(argv) != 2:
        print("usage: python cli.py <readings-file>")
        return 2
    readings = drop_outliers(load(argv[1]))
    print(summarize(readings))
    print("rounded mean: %d" % round(stats.mean(readings)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
