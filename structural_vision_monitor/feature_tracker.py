import numpy as np
import cv2


def pixel_to_mm(signal, scale_factor):
    """
    Convert pixel-displacement signal to physical units (mm).

    Parameters
    ----------
    signal      : array-like
    scale_factor : float  [mm / pixel]

    Returns
    -------
    np.ndarray in mm
    """
    return np.asarray(signal, dtype=np.float64) * scale_factor


def calibrate_from_ruler(frame, known_mm, axis="horizontal"):
    """
    Interactive calibration: user clicks two points on a ruler/reference
    object of known physical length to derive a mm/pixel scale factor.

    Parameters
    ----------
    frame    : np.ndarray  BGR image used for calibration
    known_mm : float       physical distance between the two click points
    axis     : str         'horizontal' | 'vertical' | 'both'
                           determines which pixel component to use

    Returns
    -------
    scale_factor : float  [mm / pixel]
    """
    points = []

    def mouse_callback(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and len(points) < 2:
            points.append((x, y))
            print(f"  Point {len(points)}: ({x}, {y})")

    clone = frame.copy()
    cv2.namedWindow("Calibration — click two reference points", cv2.WINDOW_NORMAL)
    cv2.setMouseCallback("Calibration — click two reference points", mouse_callback)

    print(f"[Calibration] Click two points {known_mm:.1f} mm apart.")
    while len(points) < 2:
        display = clone.copy()
        for p in points:
            cv2.circle(display, p, 5, (0, 255, 0), -1)
        cv2.imshow("Calibration — click two reference points", display)
        if cv2.waitKey(10) & 0xFF == 27:
            break

    cv2.destroyAllWindows()

    if len(points) < 2:
        raise RuntimeError("Calibration cancelled — fewer than 2 points selected.")

    p1, p2 = np.array(points[0], dtype=float), np.array(points[1], dtype=float)
    diff = p2 - p1

    if axis == "horizontal":
        pixel_dist = abs(diff[0])
    elif axis == "vertical":
        pixel_dist = abs(diff[1])
    else:
        pixel_dist = np.linalg.norm(diff)

    if pixel_dist < 1:
        raise ValueError("Points too close together for reliable calibration.")

    scale = known_mm / pixel_dist
    print(f"[Calibration] Scale factor: {scale:.5f} mm/pixel")
    return scale


def calibrate_from_chessboard(frame, square_size_mm=25.0, board_size=(9, 6)):
    """
    Automatic calibration using a printed chessboard.

    Parameters
    ----------
    frame          : np.ndarray  BGR frame
    square_size_mm : float  physical size of one chessboard square in mm
    board_size     : tuple  (cols-1, rows-1) inner corners

    Returns
    -------
    scale_factor : float  [mm / pixel]  (average across detected squares)
    None if pattern not found.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
    ret, corners = cv2.findChessboardCorners(gray, board_size)

    if not ret:
        print("[Calibration] Chessboard pattern not found.")
        return None

    corners = cv2.cornerSubPix(
        gray, corners, (11, 11), (-1, -1),
        (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
    )

    # Estimate pixel size of one square from horizontal neighbour spacing
    cols = board_size[0]
    spacings = []
    for r in range(board_size[1]):
        for c in range(cols - 1):
            idx_a = r * cols + c
            idx_b = r * cols + c + 1
            spacings.append(np.linalg.norm(corners[idx_a][0] - corners[idx_b][0]))

    pixel_per_square = float(np.median(spacings))
    scale = square_size_mm / pixel_per_square
    print(f"[Calibration] Chessboard scale: {scale:.5f} mm/pixel")
    return scale
