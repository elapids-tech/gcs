#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, json, cv2, numpy as np

VIDEO_PATH = "src/calculate_lens_distortion/20251025213416.mp4"
OUTPUT_JSON = "src/calculate_lens_distortion/camera_calibration_result.json"
VID_USED    = "src/calculate_lens_distortion/calib_used_frames.mp4"

COLS, ROWS = 4, 11
SAMPLE_EVERY = 3
MAX_SAMPLES  = 120
MIN_SAMPLES  = 12

COL_PITCH_MM = 20.0
ROW_PITCH_MM = None

def build_asym_points(cols, rows, col_pitch, row_pitch=None):
    if row_pitch is None:
        row_pitch = col_pitch / 2.0
    objp = np.zeros((rows * cols, 3), np.float32)
    k = 0
    for r in range(rows):
        xshift = 0.5 * col_pitch if (r % 2) == 1 else 0.0
        for c in range(cols):
            objp[k] = [c * col_pitch + xshift, r * row_pitch, 0.0]
            k += 1
    return objp

def make_blob_detector():
    p = cv2.SimpleBlobDetector_Params()
    p.filterByColor = True
    p.blobColor = 255
    p.filterByArea = True
    p.minArea = 10
    p.maxArea = 5000
    p.filterByCircularity = False
    p.filterByInertia = False
    p.filterByConvexity = False
    p.minDistBetweenBlobs = 5
    return cv2.SimpleBlobDetector_create(p)

def binarize(gray):
    g = cv2.medianBlur(gray, 3)
    _, bw = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    return bw

def try_modes_asymmetric_fixed(img_bw, detector, pattern_size):
    flag = cv2.CALIB_CB_ASYMMETRIC_GRID | cv2.CALIB_CB_CLUSTERING
    tests = [("BW", img_bw), ("BW_INV", 255 - img_bw)]
    for name, im in tests:
        ok, centers = cv2.findCirclesGrid(im, pattern_size, flags=flag, blobDetector=detector)
        if ok:
            return True, name, centers
    return False, None, None

def main():
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    os.makedirs(os.path.dirname(VID_USED), exist_ok=True)

    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        raise FileNotFoundError(f"open fail: {VIDEO_PATH}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h  = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    writer_used = cv2.VideoWriter(VID_USED, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))

    pattern_size = (COLS, ROWS)
    objp = build_asym_points(COLS, ROWS, COL_PITCH_MM, ROW_PITCH_MM)
    detector = make_blob_detector()

    objpoints, imgpoints = [], []
    last_size = None
    used = 0
    idx = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % SAMPLE_EVERY != 0:
            idx += 1
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        bw = binarize(gray)
        last_size = (w, h)

        ok_grid, mode, centers = try_modes_asymmetric_fixed(bw, detector, pattern_size)
        vis_src = bw if mode == "BW" else (255 - bw)
        vis = cv2.cvtColor(vis_src, cv2.COLOR_GRAY2BGR)
        if ok_grid:
            cv2.drawChessboardCorners(vis, pattern_size, centers, ok_grid)
            objpoints.append(objp)
            imgpoints.append(centers)
            used += 1
        writer_used.write(vis)

        if used >= MAX_SAMPLES:
            break
        idx += 1

    cap.release()
    writer_used.release()

    result = {
        "pattern": {"cols": COLS, "rows": ROWS, "type": "asymmetric"},
        "detections_total": int(used),
        "image_size_wh": list(last_size) if last_size else None,
        "videos": {"used": VID_USED},
        "physical": {
            "col_pitch_mm": COL_PITCH_MM,
            "row_pitch_mm": (ROW_PITCH_MM if ROW_PITCH_MM is not None else COL_PITCH_MM / 2.0)
        }
    }

    if used >= MIN_SAMPLES and last_size is not None:
        # fisheye.calibrate 用に形状を合わせる
        obj_f = [op.reshape(1, -1, 3).astype(np.float64) for op in objpoints]
        img_f = [ip.reshape(1, -1, 2).astype(np.float64) for ip in imgpoints]
        K = np.zeros((3,3), dtype=np.float64)
        D = np.zeros((4,1), dtype=np.float64)
        flags = (cv2.fisheye.CALIB_RECOMPUTE_EXTRINSIC |
                 cv2.fisheye.CALIB_CHECK_COND |
                 cv2.fisheye.CALIB_FIX_SKEW)
        crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_COUNT, 100, 1e-6)
        rms, K, D, rvecs, tvecs = cv2.fisheye.calibrate(
            obj_f, img_f, last_size, K, D, None, None, flags=flags, criteria=crit
        )

        # solvePnP 用のピンホール等価（歪みゼロ）行列
        newK = cv2.fisheye.estimateNewCameraMatrixForUndistortRectify(
            K, D, last_size, np.eye(3), balance=0.0
        )

        result.update({
            "calibration_model": "fisheye",
            "rms": float(rms),
            "K_fisheye": K.tolist(),
            "D_fisheye": D.reshape(-1).tolist(),          # k1..k4
            "K_pinhole": newK.tolist(),                   # solvePnP に渡す
            "dist_pinhole": [0.0, 0.0, 0.0, 0.0]          # solvePnP では歪みゼロで使用
        })
    else:
        result.update({
            "calibration_performed": False,
            "reason": f"detections {used} < MIN_SAMPLES {MIN_SAMPLES}"
        })

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

    print(json.dumps(result, indent=4, ensure_ascii=False))
    print(f"Saved: {OUTPUT_JSON}\nVideo: {VID_USED}")

if __name__ == "__main__":
    main()
