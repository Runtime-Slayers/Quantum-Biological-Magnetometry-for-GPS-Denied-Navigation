import numpy as np

def dead_reckoning_nav(B_field_sequence, dt=0.1, heading_init=0.0):
    headings = [heading_init]
    for i in range(1, len(B_field_sequence)):
        delta_B = B_field_sequence[i] - B_field_sequence[i-1]
        d_heading = np.degrees(np.arctan2(delta_B[1], delta_B[0]))
        headings.append(headings[-1] + d_heading * dt)
    return np.array(headings)
