import os

import cv2
import numpy as np
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

        accepted = False
        if ok_grid and centers is not None:
            accepted = cc.add_grid_points(centers, image_shape=gray.shape[:2])

        annotated = cc.draw_detected_points(frame, centers)

        frame_path = os.path.join(frames_dir, f"frame_{frame_count:05d}.png")
        cv2.imwrite(frame_path, annotated)

        if accepted:
            update_result = cc.get_tile_overlap_count()
        else:
            update_result = None

        if update_result is not None:
            blended = cc.draw_overlay(annotated, update_result, alpha=0.5, max_count=10)
            overlay_path = os.path.join(overlay_dir, f"overlay_{frame_count:05d}.png")
            cv2.imwrite(overlay_path, blended)
        

    cap.release()

    if frame_count == 0:
        pytest.skip("video has no frames")

    cc.execute_calibration()
    result = cc.get_result()
    print(result)
    assert result is not None
    assert "pattern" in result
    assert "detections_total" in result

