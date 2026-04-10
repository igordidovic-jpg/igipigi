if fake_control:
    if losing_side == "HOME":
        lam_h_raw *= 1.28
        lam_a_raw *= 0.88
    else:
        lam_a_raw *= 1.28
        lam_h_raw *= 0.88