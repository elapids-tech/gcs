import os

import cv2
import pytest

from backend.camera_calibration import CameraCalibration


def test_camera_calibration():
    video_path = "/idls_app/backend/test/data/binarized_frames.mp4"
    if not os.path.exists(video_path):
        pytest.skip(f"missing video: {video_path}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        pytest.skip(f"open fail: {video_path}")

    cc = CameraCalibration(cols=4, rows=11, col_pitch_mm=20.0, row_pitch_mm=None)

    output_dir = os.environ.get("CALIBRATION_OUTPUT_DIR", "/idls_app/backend/test/output")
    frames_dir = os.path.join(output_dir, "frames")
    overlay_dir = os.path.join(output_dir, "overlay")
    os.makedirs(frames_dir, exist_ok=True)
    os.makedirs(overlay_dir, exist_ok=True)

    frame_count = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame_count += 1
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        bw = cc.binarize(gray)
        ok_grid, centers = cc.find_asymmetric_grid(bw)

        update_result = None
        if ok_grid and centers is not None:
            update_result = cc.add_grid_points(centers, image_shape=gray.shape[:2])

        centers = centers.reshape(-1, 2) if ok_grid and centers is not None else None

        annotated = frame.copy()
        if centers is not None:
            for idx, (x, y) in enumerate(centers):
                cx, cy = int(round(x)), int(round(y))
                cv2.circle(annotated, (cx, cy), 4, (0, 255, 0), -1)
                cv2.putText(
                    annotated,
                    str(idx),
                    (cx + 5, cy - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    (0, 255, 0),
                    1,
                    cv2.LINE_AA,
                )

        frame_path = os.path.join(frames_dir, f"frame_{frame_count:05d}.png")
        cv2.imwrite(frame_path, annotated)

        if update_result is not None:
            overlay_path = os.path.join(overlay_dir, f"overlay_{frame_count:05d}.png")
            cv2.imwrite(overlay_path, update_result)
        

    cap.release()

    if frame_count == 0:
        pytest.skip("video has no frames")

    cc.execute_calibration()
    result = cc.get_result()
    print(result)
    assert result is not None
    assert "pattern" in result
    assert "detections_total" in result

