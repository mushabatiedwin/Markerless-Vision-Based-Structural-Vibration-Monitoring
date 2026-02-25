import cv2
import numpy as np


class VibrationTracker:
    """
    Markerless optical-flow vibration tracker with:
    - Shi-Tomasi feature detection
    - Lucas-Kanade sparse optical flow
    - Homography-based global camera motion removal
    - Optional ROI for structure isolation
    - Feature reinitialization on track loss
    """

    def __init__(self, video_path, roi=None, reinit_interval=60):
        """
        Parameters
        ----------
        video_path : str
            Path to input video file.
        roi : tuple or None
            (x, y, w, h) pixel region defining the structure of interest.
            If None, the full frame is used (no separation of background).
        reinit_interval : int
            Re-detect features every N frames to recover from drift / track loss.
        """
        self.video_path = video_path
        self.roi = roi
        self.reinit_interval = reinit_interval

        self.feature_params = dict(
            maxCorners=400,
            qualityLevel=0.01,
            minDistance=7,
            blockSize=7,
        )

        self.lk_params = dict(
            winSize=(21, 21),
            maxLevel=3,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self):
        """
        Track features across every frame and return per-frame displacement lists.

        Returns
        -------
        all_displacements : list of np.ndarray  shape (N_i, 2)
            Raw (dx, dy) vectors for each tracked feature in frame i.
        fps : float
        """
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {self.video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30.0  # safe fallback

        ret, old_frame = cap.read()
        if not ret:
            raise ValueError("Cannot read first frame.")

        old_gray = cv2.cvtColor(old_frame, cv2.COLOR_BGR2GRAY)
        p0 = self._detect_features(old_gray)
        origin = p0.copy()           # anchor for absolute displacement

        all_displacements = []
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_idx += 1

            frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            p1, st, err = cv2.calcOpticalFlowPyrLK(
                old_gray, frame_gray, p0, None, **self.lk_params
            )

            if p1 is None or np.sum(st) < 8:
                # Re-initialize on catastrophic track failure
                p0 = self._detect_features(frame_gray)
                origin = p0.copy()
                old_gray = frame_gray.copy()
                all_displacements.append(np.zeros((1, 2), dtype=np.float32))
                continue

            good_new = p1[st.ravel() == 1]
            good_old = p0[st.ravel() == 1]

            # --- Homography-based camera motion removal ---
            frame_disp = self._compensate_homography(good_old, good_new, frame_gray.shape)

            all_displacements.append(frame_disp)

            old_gray = frame_gray.copy()
            p0 = good_new.reshape(-1, 1, 2)

            # Periodic feature re-initialization to fight drift
            if frame_idx % self.reinit_interval == 0:
                new_pts = self._detect_features(frame_gray)
                p0 = new_pts
                origin = p0.copy()

        cap.release()
        return all_displacements, fps

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _detect_features(self, gray):
        mask = None
        if self.roi is not None:
            x, y, w, h = self.roi
            mask = np.zeros_like(gray)
            mask[y : y + h, x : x + w] = 255
        pts = cv2.goodFeaturesToTrack(gray, mask=mask, **self.feature_params)
        if pts is None:
            raise RuntimeError("No features detected. Check video content or ROI.")
        return pts

    def _compensate_homography(self, pts_old, pts_new, frame_shape):
        """
        Estimate global camera motion via homography and subtract it from
        per-feature displacements so only structural motion remains.

        Falls back to median subtraction when homography cannot be estimated.
        """
        if len(pts_old) < 8:
            # Not enough points for homography → median fallback
            raw = pts_new - pts_old
            cam_motion = np.median(raw, axis=0)
            return raw - cam_motion

        H, inlier_mask = cv2.findHomography(
            pts_old.reshape(-1, 1, 2),
            pts_new.reshape(-1, 1, 2),
            cv2.RANSAC,
            ransacReprojThreshold=3.0,
        )

        if H is None:
            raw = pts_new - pts_old
            cam_motion = np.median(raw, axis=0)
            return raw - cam_motion

        # Project old points through H → predicted new positions if camera-only motion
        h, w = frame_shape
        pts_old_h = pts_old.reshape(-1, 1, 2).astype(np.float32)
        predicted = cv2.perspectiveTransform(pts_old_h, H).reshape(-1, 2)

        # Residual after removing camera motion = structural displacement
        structural = pts_new - predicted
        return structural.astype(np.float32)
