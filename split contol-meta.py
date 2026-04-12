# ============================================================
# SPLIT CONTROL META CORRECTION
# ============================================================

if split_control:
    mc_x_adj *= 1.35      # draw boost
    mc_a_adj *= 0.80      # away reduce
    mc_h_adj *= 1.10      # home slight boost

    total = mc_h_adj + mc_x_adj + mc_a_adj
    mc_h_adj /= total
    mc_x_adj /= total
    mc_a_adj /= total