"""
CFOS-XG PRO 75 TITAN - Momentum Detector Module

Detects momentum, tempo, and pressure patterns from match statistics.
"""


class MomentumDetector:
    """
    Detects and quantifies match momentum from live statistics.

    Momentum is a composite score based on:
    - Shot advantage
    - Dangerous attack advantage
    - Expected goals rate
    - Recent scoring events
    """

    @staticmethod
    def calculate_momentum(
        shots_h: float, shots_a: float,
        danger_h: float, danger_a: float,
        xg_h: float, xg_a: float,
        sot_h: float, sot_a: float,
    ) -> float:
        """
        Calculate match momentum score.

        Args:
            shots_h / shots_a: Total shots for home / away
            danger_h / danger_a: Dangerous attacks for home / away
            xg_h / xg_a: Expected goals for home / away
            sot_h / sot_a: Shots on target for home / away

        Returns:
            Momentum value: positive = home momentum, negative = away
        """
        def _diff_ratio(h, a):
            total = h + a
            if total <= 0:
                return 0.0
            return (h - a) / total

        shot_mom = _diff_ratio(shots_h, shots_a) * 0.20
        danger_mom = _diff_ratio(danger_h, danger_a) * 0.35
        xg_mom = _diff_ratio(xg_h, xg_a) * 0.30
        sot_mom = _diff_ratio(sot_h, sot_a) * 0.15

        raw = shot_mom + danger_mom + xg_mom + sot_mom
        return max(-1.0, min(1.0, raw))

    @staticmethod
    def classify_tempo(
        shots: float, danger: float, attacks: float, minute: int
    ) -> str:
        """
        Classify match tempo based on rate of statistics.

        Args:
            shots: Total shots
            danger: Total dangerous attacks
            attacks: Total attacks
            minute: Current match minute

        Returns:
            Tempo label: "HIGH", "MEDIUM", or "LOW"
        """
        if minute <= 0:
            return "LOW"

        shots_per_min = shots / minute
        danger_per_min = danger / minute

        if shots_per_min >= 0.28 or danger_per_min >= 1.40:
            return "HIGH"
        if shots_per_min >= 0.18 or danger_per_min >= 0.90:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def detect_attack_wave(
        shots_h: float, shots_a: float,
        danger_h: float, danger_a: float,
        minute: int,
    ) -> dict:
        """
        Detect whether an attack wave is in progress.

        Returns:
            dict with keys:
                - active (bool): Whether attack wave is active
                - side (str): "HOME", "AWAY", or "BOTH"
                - intensity (float): Wave intensity 0.0-1.0
        """
        total_shots = shots_h + shots_a
        total_danger = danger_h + danger_a

        wave_active = (
            total_shots >= 14 and
            total_danger >= 90
        )

        if not wave_active:
            return {"active": False, "side": "NONE", "intensity": 0.0}

        intensity = min(1.0, total_danger / 150.0)

        if danger_h > danger_a * 1.8:
            side = "HOME"
        elif danger_a > danger_h * 1.8:
            side = "AWAY"
        else:
            side = "BOTH"

        return {"active": True, "side": side, "intensity": round(intensity, 3)}
