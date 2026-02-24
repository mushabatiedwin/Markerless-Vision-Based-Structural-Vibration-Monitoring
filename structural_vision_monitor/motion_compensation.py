import numpy as np

def compensate_motion(displacements, roi=None):
    corrected_signal = []

    for frame_disp in displacements:
        if len(frame_disp) == 0:
            corrected_signal.append(0)
            continue

        structure_disp = []
        background_disp = []

        for dx, dy in frame_disp:
            if roi is not None:
                x, y, w, h = roi
                # NOTE: You must ensure ROI selection matches feature coordinates.
                # For now, assume ROI applied externally if needed.
                structure_disp.append([dx, dy])
            else:
                structure_disp.append([dx, dy])

        structure_disp = np.array(structure_disp)

        if len(background_disp) > 0:
            camera_motion = np.median(background_disp, axis=0)
        else:
            camera_motion = np.array([0, 0])

        corrected = structure_disp - camera_motion
        y_vals = corrected[:, 1]

        median = np.median(y_vals)
        mad = np.median(np.abs(y_vals - median))

        if mad == 0:
            avg_y = median
        else:
            mask = np.abs(y_vals - median) < 3 * mad
            filtered = y_vals[mask]
            avg_y = np.mean(filtered) if len(filtered) > 0 else median


        corrected_signal.append(avg_y)

    return np.array(corrected_signal)
