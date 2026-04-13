"""
CFOS-XG PRO 75 TITAN - Lambda Calculator Module

Wraps the Poisson/lambda calculation functions from the core engine.
"""
import math
import sys
import os

# Add parent directory to path so LUCKY-7-92 can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class LambdaCalculator:
    """
    Calculates expected goal rates (lambda) for home and away teams.

    Uses Poisson distribution and Bivariate Poisson model to estimate
    the rate of goal scoring based on match statistics.
    """

    @staticmethod
    def poisson_pmf(k: int, lam: float) -> float:
        """Compute Poisson probability mass function P(X=k) for rate lam."""
        if lam <= 0:
            return 1.0 if k == 0 else 0.0
        try:
            return math.exp(-lam) * (lam ** k) / math.factorial(k)
        except (OverflowError, ValueError):
            return 0.0

    @staticmethod
    def prob_goal_in_window(lam: float, minutes: float) -> float:
        """
        Probability of at least one goal in given number of minutes.

        Args:
            lam: Goal rate per 90 minutes
            minutes: Time window in minutes

        Returns:
            Probability of at least 1 goal
        """
        if lam <= 0 or minutes <= 0:
            return 0.0
        lam_window = lam * (minutes / 90.0)
        return 1.0 - math.exp(-lam_window)

    @staticmethod
    def time_adjusted_lambda(lam: float, minute: int) -> float:
        """
        Adjusts lambda for remaining match time.

        Args:
            lam: Raw lambda (full match rate)
            minute: Current match minute

        Returns:
            Time-adjusted lambda for remaining time
        """
        if minute >= 90:
            remaining = 7  # injury time
        else:
            remaining = max(1, 95 - minute)
        return lam * (remaining / 90.0)

    @staticmethod
    def p_goal_from_lambda(lam_h: float, lam_a: float, lam_c: float, minute: int) -> float:
        """
        Probability of any goal in remaining match time.

        Args:
            lam_h: Home team lambda (goals per 90 min)
            lam_a: Away team lambda
            lam_c: Shared/correlation lambda
            minute: Current match minute

        Returns:
            Probability of at least one more goal
        """
        if minute >= 90:
            remaining = 7
        else:
            remaining = max(1, 95 - minute)

        total_lam = (lam_h + lam_a + lam_c) * (remaining / 90.0)
        if total_lam <= 0:
            return 0.0
        return 1.0 - math.exp(-total_lam)

    @staticmethod
    def next_goal_probs(lam_h: float, lam_a: float) -> tuple[float, float]:
        """
        Probability that the next goal is scored by home vs away team.

        Args:
            lam_h: Home lambda
            lam_a: Away lambda

        Returns:
            Tuple of (p_home_next, p_away_next)
        """
        total = lam_h + lam_a
        if total <= 0:
            return 0.5, 0.5
        return lam_h / total, lam_a / total
