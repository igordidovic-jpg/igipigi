"""
Unit tests for LambdaCalculator module.
"""
import math
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.lambda_calculator import LambdaCalculator


class TestPoissonPmf:
    def test_zero_lambda_k0(self):
        assert LambdaCalculator.poisson_pmf(0, 0.0) == 1.0

    def test_zero_lambda_k1(self):
        assert LambdaCalculator.poisson_pmf(1, 0.0) == 0.0

    def test_known_value(self):
        # P(X=0 | lam=1.0) = e^-1 ≈ 0.3679
        result = LambdaCalculator.poisson_pmf(0, 1.0)
        assert abs(result - math.exp(-1.0)) < 1e-6

    def test_negative_lambda(self):
        assert LambdaCalculator.poisson_pmf(0, -1.0) == 1.0

    def test_probabilities_sum_to_one(self):
        lam = 1.5
        total = sum(LambdaCalculator.poisson_pmf(k, lam) for k in range(15))
        assert abs(total - 1.0) < 0.001


class TestProbGoalInWindow:
    def test_zero_lambda(self):
        assert LambdaCalculator.prob_goal_in_window(0.0, 10) == 0.0

    def test_zero_minutes(self):
        assert LambdaCalculator.prob_goal_in_window(1.5, 0) == 0.0

    def test_full_match(self):
        # Full 90 minute window with lam=1.5 -> p = 1 - e^-1.5
        result = LambdaCalculator.prob_goal_in_window(1.5, 90)
        expected = 1.0 - math.exp(-1.5)
        assert abs(result - expected) < 1e-6

    def test_probability_between_0_and_1(self):
        for lam in [0.5, 1.0, 2.0, 3.0]:
            for minutes in [5, 10, 20, 45, 90]:
                p = LambdaCalculator.prob_goal_in_window(lam, minutes)
                assert 0.0 <= p <= 1.0


class TestNextGoalProbs:
    def test_equal_lambdas(self):
        p_h, p_a = LambdaCalculator.next_goal_probs(1.0, 1.0)
        assert abs(p_h - 0.5) < 1e-9
        assert abs(p_a - 0.5) < 1e-9

    def test_zero_total(self):
        p_h, p_a = LambdaCalculator.next_goal_probs(0.0, 0.0)
        assert p_h == 0.5
        assert p_a == 0.5

    def test_home_dominant(self):
        p_h, p_a = LambdaCalculator.next_goal_probs(3.0, 1.0)
        assert p_h > p_a
        assert abs(p_h - 0.75) < 1e-9

    def test_probs_sum_to_one(self):
        for lam_h, lam_a in [(1.0, 2.0), (0.5, 0.5), (2.5, 0.3)]:
            p_h, p_a = LambdaCalculator.next_goal_probs(lam_h, lam_a)
            assert abs(p_h + p_a - 1.0) < 1e-9


class TestTimeAdjustedLambda:
    def test_at_minute_45(self):
        # 50 minutes remaining (95-45)
        result = LambdaCalculator.time_adjusted_lambda(1.8, 45)
        expected = 1.8 * (50 / 90.0)
        assert abs(result - expected) < 1e-9

    def test_at_minute_90_plus(self):
        # 7 injury time minutes
        result = LambdaCalculator.time_adjusted_lambda(1.8, 90)
        expected = 1.8 * (7 / 90.0)
        assert abs(result - expected) < 1e-9

    def test_never_negative(self):
        for minute in [0, 30, 60, 90, 95, 120]:
            result = LambdaCalculator.time_adjusted_lambda(1.5, minute)
            assert result >= 0.0
