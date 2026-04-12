# ============================================================
# SCORE BALANCER (ANTI DOMINATION BUG)
# ============================================================

score_diff = abs(score_h - score_a)

if score_diff > 0.35:
    score_h *= 0.85
    score_a *= 0.85