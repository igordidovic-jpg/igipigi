# ============================================================
# LAMBDA RATIO HARD LIMIT (CRITICAL FIX)
# ============================================================

lam_ratio = lam_away / max(lam_home, 1e-6)

if lam_ratio > 3.0:
    scale = 3.0 / lam_ratio
    lam_away *= scale