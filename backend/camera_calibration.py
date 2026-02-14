import json
import cv2
import numpy as np

class CameraCalibration:
    def __init__(
        self,
        cols,
        rows,
        col_pitch_mm,
        row_pitch_mm=None,
        max_samples=120,
        min_samples=12,
        target_rms=None,
        overlay_scale=0.25,
        output_json_path=None,
    ):
        self.result = None
        self.cols = cols
        self.rows = rows
        self.col_pitch_mm = col_pitch_mm
        self.row_pitch_mm = row_pitch_mm if row_pitch_mm is not None else col_pitch_mm / 2.0
        self.max_samples = max_samples
        self.min_samples = min_samples
        self.target_rms = target_rms
        self.overlay_scale = overlay_scale
        self.output_json_path = output_json_path

        self._pattern_size = (self.cols, self.rows)
        self._objp = self.build_asym_points(self.cols, self.rows, self.col_pitch_mm, self.row_pitch_mm)
        self._detector = self.make_blob_detector()
        self._objpoints = []
        self._imgpoints = []
        self._last_size = None
        self._complete = False
        self._tile_counts = None
        self._tile_grid = None
        self._tile_size = 50

    def build_asym_points(self, cols, rows, col_pitch, row_pitch):
        objp = np.zeros((rows * cols, 3), np.float32)
        k = 0
        for r in range(rows):
            xshift = 0.5 * col_pitch if (r % 2) == 1 else 0.0
            for c in range(cols):
                objp[k] = [c * col_pitch + xshift, r * row_pitch, 0.0]
                k += 1
        return objp

    def make_blob_detector(self):
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

    def binarize(self, gray):
        g = cv2.medianBlur(gray, 3)
        _, bw = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
        return bw

    def _find_asymmetric_grid(self, img_bw):
        flag = cv2.CALIB_CB_ASYMMETRIC_GRID | cv2.CALIB_CB_CLUSTERING
        tests = [img_bw, 255 - img_bw]
        for im in tests:
            ok, centers = cv2.findCirclesGrid(im, self._pattern_size, flags=flag, blobDetector=self._detector)
            if ok:
                return True, centers
        return False, None

    def update(self, frame):
        if self._complete:
            return None
        if frame is None:
            return None

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        bw = self.binarize(gray)
        h, w = gray.shape[:2]
        self._last_size = (w, h)

        tile_size = self._tile_size
        grid_cols = (w + tile_size - 1) // tile_size
        grid_rows = (h + tile_size - 1) // tile_size
        grid_shape = (grid_rows, grid_cols)
        if self._tile_counts is None or self._tile_grid != grid_shape:
            self._tile_counts = np.zeros(grid_shape, dtype=np.int32)
            self._tile_grid = grid_shape

        ok_grid, centers = self._find_asymmetric_grid(bw)
        if ok_grid and centers is not None:
            self._objpoints.append(self._objp)
            self._imgpoints.append(centers)

        if len(self._objpoints) > self.max_samples:
            self._objpoints = self._objpoints[: self.max_samples]
            self._imgpoints = self._imgpoints[: self.max_samples]

        self._build_result()
        if ok_grid and centers is not None:
            outer = self.get_outer_points(centers)
            if outer:
                poly = np.asarray(outer, dtype=np.int32).reshape(-1, 1, 2)
                mask = np.zeros((h, w), dtype=np.uint8)
                cv2.fillPoly(mask, [poly], 1)

                for row in range(grid_rows):
                    y0 = row * tile_size
                    y1 = min((row + 1) * tile_size, h)
                    for col in range(grid_cols):
                        x0 = col * tile_size
                        x1 = min((col + 1) * tile_size, w)
                        if np.any(mask[y0:y1, x0:x1]):
                            self._tile_counts[row, col] += 1

        overlay = np.zeros((h, w, 3), dtype=np.uint8)
        for row in range(grid_rows):
            y0 = row * tile_size
            y1 = min((row + 1) * tile_size, h)
            for col in range(grid_cols):
                x0 = col * tile_size
                x1 = min((col + 1) * tile_size, w)
                count = int(self._tile_counts[row, col])
                t = min(count, 10) / 10.0
                value = int(round((1.0 - t) * 255.0))
                color = cv2.applyColorMap(
                    np.array([[value]], dtype=np.uint8),
                    cv2.COLORMAP_JET,
                )[0, 0]
                overlay[y0:y1, x0:x1] = color

        if self.overlay_scale != 1.0:
            overlay = cv2.resize(
                overlay,
                (max(1, int(round(w * self.overlay_scale))), max(1, int(round(h * self.overlay_scale)))),
                interpolation=cv2.INTER_NEAREST,
            )

        return overlay

    def _build_result(self):
        used = len(self._objpoints)
        result = {
            "pattern": {"cols": self.cols, "rows": self.rows, "type": "asymmetric"},
            "detections_total": int(used),
            "image_size_wh": list(self._last_size) if self._last_size else None,
            "physical": {
                "col_pitch_mm": self.col_pitch_mm,
                "row_pitch_mm": self.row_pitch_mm,
            },
            "target_rms": self.target_rms,
        }

        if used >= self.min_samples and self._last_size is not None:
            obj_f = [op.reshape(1, -1, 3).astype(np.float64) for op in self._objpoints]
            img_f = [ip.reshape(1, -1, 2).astype(np.float64) for ip in self._imgpoints]
            K = np.zeros((3, 3), dtype=np.float64)
            D = np.zeros((4, 1), dtype=np.float64)
            flags = (
                cv2.fisheye.CALIB_RECOMPUTE_EXTRINSIC
                | cv2.fisheye.CALIB_CHECK_COND
                | cv2.fisheye.CALIB_FIX_SKEW
            )
            crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_COUNT, 100, 1e-6)
            rms, K, D, rvecs, tvecs = cv2.fisheye.calibrate(
                obj_f,
                img_f,
                self._last_size,
                K,
                D,
                None,
                None,
                flags=flags,
                criteria=crit,
            )

            newK = cv2.fisheye.estimateNewCameraMatrixForUndistortRectify(
                K, D, self._last_size, np.eye(3), balance=0.0
            )

            result.update(
                {
                    "calibration_model": "fisheye",
                    "rms": float(rms),
                    "K_fisheye": K.tolist(),
                    "D_fisheye": D.reshape(-1).tolist(),
                    "K_pinhole": newK.tolist(),
                    "dist_pinhole": [0.0, 0.0, 0.0, 0.0],
                }
            )
            if self.target_rms is not None:
                self._complete = float(rms) <= self.target_rms
                result["calibration_complete"] = self._complete
        else:
            result.update(
                {
                    "calibration_performed": False,
                    "reason": f"detections {used} < min_samples {self.min_samples}",
                }
            )
            if self.target_rms is not None:
                result["calibration_complete"] = False

        self.result = result

    def get_outer_points(self, centers):
        if centers is None:
            return None

        pts = np.asarray(centers, dtype=np.float32)
        if pts.ndim == 3 and pts.shape[1:] == (1, 2):
            pts = pts.reshape(-1, 2)
        elif pts.ndim != 2 or pts.shape[1] != 2:
            raise ValueError("centers must be a Nx2 array or Nx1x2 array")

        expected = self.rows * self.cols
        if pts.shape[0] != expected:
            raise ValueError("centers size does not match pattern size")

        outer_indices = [0, 1, 2, 3, 7, 15, 23, 31, 39, 43, 42, 41, 40, 32, 24, 16, 8]
        if max(outer_indices) >= pts.shape[0]:
            raise ValueError("centers size does not match outer index list")
        outer = [pts[idx].tolist() for idx in outer_indices]

        return outer

    def output_result_json(self, output_path=None):
        if self.result is None:
            raise ValueError("No calibration result available")

        path = output_path or self.output_json_path
        if not path:
            raise ValueError("output path is required")

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.result, f, indent=4, ensure_ascii=False)

    def get_result(self):
        if self.result is None:
            return None
        return dict(self.result)

