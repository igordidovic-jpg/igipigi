"""
Unit tests for BetScorer module.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.bet_scorer import BetScorer, CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, CONFIDENCE_LOW


class TestGetConfidenceLabel:
    def test_high_confidence(self):
        assert BetScorer.get_confidence_label(8.0, 1.5) == CONFIDENCE_HIGH

    def test_medium_confidence(self):
        assert BetScorer.get_confidence_label(6.0, 0.6) == CONFIDENCE_MEDIUM

    def test_low_confidence_low_score(self):
        assert BetScorer.get_confidence_label(4.0, 0.5) == CONFIDENCE_LOW

    def test_low_confidence_low_gap(self):
        assert BetScorer.get_confidence_label(8.0, 0.3) == CONFIDENCE_LOW

    def test_boundary_high(self):
        assert BetScorer.get_confidence_label(7.5, 1.0) == CONFIDENCE_HIGH

    def test_boundary_medium(self):
        assert BetScorer.get_confidence_label(5.5, 0.5) == CONFIDENCE_MEDIUM


class TestGetValidWindow:
    def test_normal_minute(self):
        assert BetScorer.get_valid_window(68) == "68-73"

    def test_near_end(self):
        assert BetScorer.get_valid_window(93) == "93-97"

    def test_cap_at_97(self):
        assert BetScorer.get_valid_window(95) == "95-97"  # capped at 97

    def test_zero_minute(self):
        assert BetScorer.get_valid_window(0) == "0-5"


class TestExtractDecision:
    def _make_result(self, top_scores=None, minute=68, home="Arsenal", away="Chelsea"):
        if top_scores is None:
            top_scores = [
                ("NEXT GOAL HOME", 8.5),
                ("NO BET", 7.2),
                ("COMEBACK AWAY", 5.8),
            ]
        return {
            "home": home,
            "away": away,
            "minute": minute,
            "score_home": 1,
            "score_away": 0,
            "p_goal": 0.72,
            "mc_h_adj": 0.64,
            "mc_x_adj": 0.25,
            "mc_a_adj": 0.11,
            "top_scores": top_scores,
        }

    def test_basic_extraction(self):
        result = self._make_result()
        d = BetScorer.extract_decision(result)
        assert d["bet"] == "NEXT GOAL HOME"
        assert d["home"] == "Arsenal"
        assert d["away"] == "Chelsea"
        assert d["minute"] == 68

    def test_confidence_high(self):
        result = self._make_result(top_scores=[
            ("NEXT GOAL HOME", 8.5),
            ("NO BET", 6.0),
        ])
        d = BetScorer.extract_decision(result)
        assert d["confidence"] == CONFIDENCE_HIGH

    def test_confidence_medium(self):
        result = self._make_result(top_scores=[
            ("DRAW", 6.0),
            ("NO BET", 5.4),
        ])
        d = BetScorer.extract_decision(result)
        assert d["confidence"] == CONFIDENCE_MEDIUM

    def test_empty_top_scores(self):
        result = self._make_result(top_scores=[])
        d = BetScorer.extract_decision(result)
        assert d["bet"] == "NO BET"

    def test_valid_window_present(self):
        result = self._make_result()
        d = BetScorer.extract_decision(result)
        assert "valid_window" in d
        assert "68" in d["valid_window"]

    def test_p_goal_in_result(self):
        result = self._make_result()
        d = BetScorer.extract_decision(result)
        assert abs(d["p_goal"] - 0.72) < 1e-6

    def test_top_scores_limited_to_5(self):
        scores = [(f"BET_{i}", float(10 - i)) for i in range(10)]
        result = self._make_result(top_scores=scores)
        d = BetScorer.extract_decision(result)
        assert len(d["top_scores"]) <= 5


class TestFormatTelegramMessage:
    def test_contains_team_names(self):
        decision = {
            "home": "Arsenal", "away": "Chelsea", "minute": 68,
            "bet": "NEXT GOAL HOME", "confidence": "HIGH",
            "valid_window": "68-73", "p_goal": 0.72,
            "mc_h": 0.64, "mc_x": 0.25, "mc_a": 0.11,
            "top_scores": [("NEXT GOAL HOME", 8.5)],
        }
        msg = BetScorer.format_telegram_message(decision, 1, 0)
        assert "Arsenal" in msg
        assert "Chelsea" in msg

    def test_contains_bet_info(self):
        decision = {
            "home": "A", "away": "B", "minute": 70,
            "bet": "NO BET", "confidence": "LOW",
            "valid_window": "70-75", "p_goal": 0.30,
            "mc_h": 0.40, "mc_x": 0.30, "mc_a": 0.30,
            "top_scores": [],
        }
        msg = BetScorer.format_telegram_message(decision)
        assert "NO BET" in msg
        assert "LOW" in msg

    def test_contains_score(self):
        decision = {
            "home": "A", "away": "B", "minute": 60,
            "bet": "DRAW", "confidence": "MEDIUM",
            "valid_window": "60-65", "p_goal": 0.50,
            "mc_h": 0.33, "mc_x": 0.34, "mc_a": 0.33,
            "top_scores": [("DRAW", 6.0)],
        }
        msg = BetScorer.format_telegram_message(decision, score_home=1, score_away=1)
        assert "1-1" in msg
