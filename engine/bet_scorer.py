"""
CFOS-XG PRO 75 TITAN - Bet Scorer Module

Scores and ranks bet types using the core engine's result dictionary.
Wraps bet_decision logic for programmatic access.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


BET_TYPES = [
    "NEXT GOAL HOME",
    "NEXT GOAL AWAY",
    "COMEBACK HOME",
    "COMEBACK AWAY",
    "DRAW",
    "NO GOAL",
    "NO BET",
]

CONFIDENCE_HIGH = "HIGH"
CONFIDENCE_MEDIUM = "MEDIUM"
CONFIDENCE_LOW = "LOW"


class BetScorer:
    """
    Scores bet types based on model output and returns structured decisions.
    """

    @staticmethod
    def get_confidence_label(top_score: float, gap: float) -> str:
        """
        Determine confidence label from top score and gap.

        Args:
            top_score: Score of the best bet
            gap: Score gap between best and second-best bet

        Returns:
            "HIGH", "MEDIUM", or "LOW"
        """
        if top_score >= 7.5 and gap >= 1.0:
            return CONFIDENCE_HIGH
        if top_score >= 5.5 and gap >= 0.5:
            return CONFIDENCE_MEDIUM
        return CONFIDENCE_LOW

    @staticmethod
    def get_valid_window(minute: int, window: int = 5) -> str:
        """
        Get validity window string for a bet.

        Args:
            minute: Current match minute
            window: Window duration in minutes

        Returns:
            Formatted string like "68-73"
        """
        end = min(minute + window, 97)
        return f"{minute}-{end}"

    @staticmethod
    def extract_decision(result: dict) -> dict:
        """
        Extract structured bet decision from model result dict.

        Args:
            result: Output from izracunaj_model()

        Returns:
            dict with keys:
                - bet (str): Bet type recommendation
                - confidence (str): HIGH/MEDIUM/LOW
                - valid_window (str): Time window like "68-73"
                - p_goal (float): Goal probability
                - mc_h / mc_x / mc_a (float): Monte Carlo probabilities
                - top_scores (list): Top 5 (bet_type, score) tuples
                - minute (int): Current match minute
                - home (str): Home team name
                - away (str): Away team name
        """
        top_scores = result.get("top_scores", [])
        minute = int(float(result.get("minute", 0) or 0))

        if not top_scores:
            return {
                "bet": "NO BET",
                "confidence": CONFIDENCE_LOW,
                "valid_window": BetScorer.get_valid_window(minute),
                "p_goal": float(result.get("p_goal", 0) or 0),
                "mc_h": float(result.get("mc_h_adj", 0) or 0),
                "mc_x": float(result.get("mc_x_adj", 0) or 0),
                "mc_a": float(result.get("mc_a_adj", 0) or 0),
                "top_scores": [],
                "minute": minute,
                "home": str(result.get("home", "") or ""),
                "away": str(result.get("away", "") or ""),
            }

        best_bet, best_score = top_scores[0]
        second_score = top_scores[1][1] if len(top_scores) > 1 else 0.0
        gap = best_score - second_score
        confidence = BetScorer.get_confidence_label(best_score, gap)

        return {
            "bet": best_bet,
            "confidence": confidence,
            "valid_window": BetScorer.get_valid_window(minute),
            "p_goal": float(result.get("p_goal", 0) or 0),
            "mc_h": float(result.get("mc_h_adj", result.get("mc_h_raw", 0)) or 0),
            "mc_x": float(result.get("mc_x_adj", result.get("mc_x_raw", 0)) or 0),
            "mc_a": float(result.get("mc_a_adj", result.get("mc_a_raw", 0)) or 0),
            "top_scores": top_scores[:5],
            "minute": minute,
            "home": str(result.get("home", "") or ""),
            "away": str(result.get("away", "") or ""),
        }

    @staticmethod
    def format_telegram_message(decision: dict, score_home: int = 0, score_away: int = 0) -> str:
        """
        Format a bet decision as a Telegram message.

        Args:
            decision: Output from extract_decision()
            score_home: Current home score
            score_away: Current away score

        Returns:
            Formatted Telegram message string
        """
        home = decision.get("home", "HOME")
        away = decision.get("away", "AWAY")
        minute = decision.get("minute", 0)
        bet = decision.get("bet", "NO BET")
        conf = decision.get("confidence", "LOW")
        valid = decision.get("valid_window", "")
        p_goal = decision.get("p_goal", 0)
        mc_h = decision.get("mc_h", 0)
        mc_x = decision.get("mc_x", 0)
        mc_a = decision.get("mc_a", 0)
        top = decision.get("top_scores", [])

        conf_emoji = {"HIGH": "🔥", "MEDIUM": "🟡", "LOW": "⚪"}.get(conf, "⚪")
        bet_emoji = "🟢" if "HOME" in bet else "🔴" if "AWAY" in bet else "🟡"

        lines = [
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"⚽ *{home} vs {away}* [{minute}']",
            f"📊 Score: {score_home}-{score_away}",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"{bet_emoji} *BET: {bet}*",
            f"{conf_emoji} CONFIDENCE: *{conf}*",
            f"⏱️ VALID: {valid} min",
            f"📊 P(GOAL): {round(p_goal * 100, 1)}%",
            f"🎯 MC: {round(mc_h * 100)}% / {round(mc_x * 100)}% / {round(mc_a * 100)}%",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ]

        if top:
            lines.append("*TOP 5 ALTERNATIVES:*")
            emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
            for i, (bt, sc) in enumerate(top[:5]):
                lines.append(f"{emojis[i]} {bt} ({round(sc, 1)})")

        return "\n".join(lines)
