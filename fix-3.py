if fake_control:
    if losing_side == "HOME":
        p_home_next *= 1.22
        p_away_next *= 0.85
    else:
        p_away_next *= 1.22
        p_home_next *= 0.85