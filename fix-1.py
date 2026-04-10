# ============================================================
# GLOBAL FAKE CONTROL DETECTOR
# ============================================================

fake_control = False

losing_side = "HOME" if score_diff < 0 else "AWAY"
leading_side = "AWAY" if score_diff < 0 else "HOME"

shots_losing = shots_h if losing_side == "HOME" else shots_a
shots_leading = shots_a if losing_side == "HOME" else shots_h

sot_losing = sot_h if losing_side == "HOME" else sot_a
sot_leading = sot_a if losing_side == "HOME" else sot_h

danger_losing = danger_h if losing_side == "HOME" else danger_a
danger_leading = danger_a if losing_side == "HOME" else danger_h

if (
    minute >= 65
    and abs(score_diff) == 1
    and shots_losing >= shots_leading * 0.70
    and sot_losing >= sot_leading * 0.60
    and tempo_danger < 1.08
    and game_type in ("BALANCED", "PRESSURE")
):
    fake_control = True