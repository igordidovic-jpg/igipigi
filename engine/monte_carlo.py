"""
CFOS-XG PRO 75 TITAN - Monte Carlo Engine Module

Parallel Monte Carlo simulation for match outcome prediction.
Uses multiprocessing for performance improvement.
"""
import math
import random
from multiprocessing import Pool, cpu_count
from typing import Optional


def _run_mc_chunk(args: tuple) -> tuple[int, int, int]:
    """
    Run a chunk of Monte Carlo simulations.

    Args:
        args: Tuple of (n_sims, lam_h, lam_a, lam_c, score_h, score_a, minute)

    Returns:
        Tuple of (home_wins, draws, away_wins)
    """
    n_sims, lam_h, lam_a, lam_c, score_h, score_a, minute = args

    # Time remaining fraction
    if minute >= 90:
        remaining = 7
    else:
        remaining = max(1, 95 - minute)
    time_frac = remaining / 90.0

    adj_lam_h = max(0.0, lam_h * time_frac)
    adj_lam_a = max(0.0, lam_a * time_frac)
    adj_lam_c = max(0.0, lam_c * time_frac)

    home_wins = 0
    draws = 0
    away_wins = 0

    for _ in range(n_sims):
        gh = _poisson_sample(adj_lam_h) + _poisson_sample(adj_lam_c)
        ga = _poisson_sample(adj_lam_a) + _poisson_sample(adj_lam_c)

        final_h = score_h + gh
        final_a = score_a + ga

        if final_h > final_a:
            home_wins += 1
        elif final_h < final_a:
            away_wins += 1
        else:
            draws += 1

    return home_wins, draws, away_wins


def _poisson_sample(lam: float) -> int:
    """Sample from Poisson distribution."""
    if lam <= 0:
        return 0
    # Cap at 30 to prevent underflow in exp(-lam) for very large rates
    L = math.exp(-min(lam, 30))
    k = 0
    p = 1.0
    # Cap at 12: practical maximum goals per remaining match window (prevents infinite loops)
    while p > L and k < 12:
        k += 1
        p *= random.random()
    return k - 1


class MonteCarloEngine:
    """
    Parallel Monte Carlo engine for football match simulation.

    Uses multiprocessing.Pool to distribute simulations across CPU cores
    for improved performance on large simulation counts.
    """

    def __init__(self, n_cores: Optional[int] = None):
        """
        Initialize MonteCarloEngine.

        Args:
            n_cores: Number of CPU cores to use. Defaults to cpu_count().
        """
        self.n_cores = n_cores or min(cpu_count(), 4)

    def simulate(
        self,
        lam_h: float,
        lam_a: float,
        lam_c: float,
        score_h: int,
        score_a: int,
        minute: int,
        n_sims: int = 40000,
    ) -> dict:
        """
        Run Monte Carlo simulation for match outcome.

        Args:
            lam_h: Home team lambda (goals per 90 min)
            lam_a: Away team lambda
            lam_c: Correlation/shared lambda
            score_h: Current home score
            score_a: Current away score
            minute: Current match minute
            n_sims: Total number of simulations

        Returns:
            dict with:
                - p_home (float): Probability home wins
                - p_draw (float): Probability draw
                - p_away (float): Probability away wins
                - n_sims (int): Actual simulations run
        """
        if n_sims <= 0 or minute >= 97:
            return {"p_home": 0.33, "p_draw": 0.34, "p_away": 0.33, "n_sims": 0}

        # Split work across cores
        chunk_size = max(1000, n_sims // self.n_cores)
        chunks = []
        remaining_sims = n_sims
        while remaining_sims > 0:
            this_chunk = min(chunk_size, remaining_sims)
            chunks.append((this_chunk, lam_h, lam_a, lam_c, score_h, score_a, minute))
            remaining_sims -= this_chunk

        # Run in parallel if multiple cores and enough work
        if self.n_cores > 1 and len(chunks) > 1 and n_sims >= 10000:
            try:
                with Pool(processes=min(self.n_cores, len(chunks))) as pool:
                    results = pool.map(_run_mc_chunk, chunks)
            except Exception:
                # Fallback to sequential
                results = [_run_mc_chunk(c) for c in chunks]
        else:
            results = [_run_mc_chunk(c) for c in chunks]

        total_h = sum(r[0] for r in results)
        total_d = sum(r[1] for r in results)
        total_a = sum(r[2] for r in results)
        total = total_h + total_d + total_a

        if total == 0:
            return {"p_home": 0.33, "p_draw": 0.34, "p_away": 0.33, "n_sims": n_sims}

        return {
            "p_home": round(total_h / total, 4),
            "p_draw": round(total_d / total, 4),
            "p_away": round(total_a / total, 4),
            "n_sims": n_sims,
        }
