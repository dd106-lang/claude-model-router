import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import stats


class MeanTests(unittest.TestCase):
    def test_mean(self):
        self.assertAlmostEqual(stats.mean([1, 2, 3, 4]), 2.5)

    def test_mean_empty(self):
        with self.assertRaises(ValueError):
            stats.mean([])


class VarianceTests(unittest.TestCase):
    def test_sample_variance(self):
        self.assertAlmostEqual(stats.variance([2, 4, 4, 4, 5, 5, 7, 9]), 32 / 7)

    def test_variance_needs_two(self):
        with self.assertRaises(ValueError):
            stats.variance([1])


class MedianTests(unittest.TestCase):
    def test_median_odd(self):
        self.assertEqual(stats.median([3, 1, 2]), 2)

    def test_median_even(self):
        self.assertAlmostEqual(stats.median([1, 2, 3, 4]), 2.5)

    def test_median_empty(self):
        with self.assertRaises(ValueError):
            stats.median([])


class SpreadTests(unittest.TestCase):
    def test_spread(self):
        self.assertEqual(stats.spread([3, 9, 4]), 6)


if __name__ == "__main__":
    unittest.main()
