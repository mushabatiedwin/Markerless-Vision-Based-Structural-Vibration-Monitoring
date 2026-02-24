import cv2
import numpy as np

class VibrationTracker:
    def __init__(self, video_path):
        self.video_path = video_path

        self.feature_params = dict(
            maxCorners=400,
            qualityLevel=0.01,
            minDistance=7,
            blockSize=7
        )

        self.lk_params = dict(
            winSize=(21, 21),
            maxLevel=3,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 20, 0.03)
        )

    def run(self):
        cap = cv2.VideoCapture(self.video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)

        ret, old_frame = cap.read()
        if not ret:
            raise ValueError("Cannot load video.")

        old_gray = cv2.cvtColor(old_frame, cv2.COLOR_BGR2GRAY)
        p0 = cv2.goodFeaturesToTrack(old_gray, mask=None, **self.feature_params)

        all_displacements = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            p1, st, err = cv2.calcOpticalFlowPyrLK(
                old_gray, frame_gray, p0, None, **self.lk_params
            )

            if p1 is None:
                break

            good_new = p1[st == 1]
            good_old = p0[st == 1]

            frame_disp = good_new - good_old
            all_displacements.append(frame_disp)

            old_gray = frame_gray.copy()
            p0 = good_new.reshape(-1, 1, 2)

        cap.release()
        return all_displacements, fps