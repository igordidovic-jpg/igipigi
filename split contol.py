# ============================================================
# SPLIT CONTROL DETECTOR (CRITICAL)
# ============================================================

split_control = False

if (
    attacks_home > attacks_away * 1.4
    and danger_home > danger_away * 1.5
    and xg_away > xg_home * 3
):
    split_control = True