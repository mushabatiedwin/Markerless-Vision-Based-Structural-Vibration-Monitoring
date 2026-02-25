import numpy as np


def compensate_motion(displacements, axis="y"):
    """
    Aggregate per-frame feature displacement vectors into a scalar signal.

    Since homography compensation is already applied inside VibrationTracker,
    this module now focuses on robust outlier-resistant aggregation.

    Parameters
    ----------
    displacements : list of np.ndarray  shape (N_i, 2)
        Output from VibrationTracker.run().
    axis : str
        'y' for vertical vibration, 'x' for horizontal, 'magnitude' for L2 norm.

    Returns
    -------
    signal : np.ndarray  shape (T,)
        Scalar displacement per frame.
    """
    axis_idx = {"x": 0, "y": 1}.get(axis, 1)
    signal = []

    for frame_disp in displacements:
        if frame_disp is None or len(frame_disp) == 0:
            signal.append(0.0)
            continue

        if axis == "magnitude":
            vals = np.linalg.norm(frame_disp, axis=1)
        else:
            vals = frame_disp[:, axis_idx]

        # Median + MAD outlier rejection (robust to point-tracking noise)
        median = np.median(vals)
        mad = np.median(np.abs(vals - median))

        if mad < 1e-9:
            signal.append(float(median))
        else:
            inlier_mask = np.abs(vals - median) < 3.0 * mad
            clean = vals[inlier_mask]
            signal.append(float(np.mean(clean)) if len(clean) > 0 else float(median))

    return np.array(signal, dtype=np.float64)
