import json
import cv2
import numpy as np

class CameraCalibration:
    LENS_TYPES = {"fisheye", "pinhole"}

    def __init__(
        self,
        cols,
        rows,
        col_pitch_mm,
        row_pitch_mm=None,
        max_samples=120,
        min_samples=12,
        output_json_path=None,
        lens_type="fisheye",
    ):
        """Initialize calibration.

        lens_type: "fisheye" or "pinhole".
        """
        self.result = None
        self.cols = cols
        self.rows = rows
        self.col_pitch_mm = col_pitch_mm
        self.row_pitch_mm = row_pitch_mm if row_pitch_mm is not None else col_pitch_mm / 2.0
        self.max_samples = max_samples
        self.min_samples = min_samples
        self.output_json_path = output_json_path
        if lens_type not in self.LENS_TYPES:
            raise ValueError(f"lens_type must be one of {sorted(self.LENS_TYPES)}")
        self.lens_type = lens_type

        self._pattern_size = (self.cols, self.rows)
        self._objp = self.build_asym_points(self.cols, self.rows, self.col_pitch_mm, self.row_pitch_mm)
        self._detector = self.make_blob_detector()
        self._objpoints = []
        self._imgpoints = []
        self._last_size = None
        self._tile_counts = None
        self._tile_grid = None
        self._tile_size = 50
        self._overlap_history = []
        self._overlap_history_set = set()
        self._overlap_history_limit = 200
        self._executing = False

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

    def find_asymmetric_grid(self, img_bw):
        flag = cv2.CALIB_CB_ASYMMETRIC_GRID | cv2.CALIB_CB_CLUSTERING
        tests = [img_bw, 255 - img_bw]
        for im in tests:
            ok, centers = cv2.findCirclesGrid(im, self._pattern_size, flags=flag, blobDetector=self._detector)
            if ok:
                return centers
        return None

    def _ensure_tile_grid(self, image_shape):
        h, w = image_shape
        tile_size = self._tile_size
        grid_cols = (w + tile_size - 1) // tile_size
        grid_rows = (h + tile_size - 1) // tile_size
        grid_shape = (grid_rows, grid_cols)
        if self._tile_counts is None or self._tile_grid != grid_shape:
            self._tile_counts = np.zeros(grid_shape, dtype=np.int32)
            self._tile_grid = grid_shape
        return grid_shape

    def _get_overlap_tiles(self, image_shape, centers):
        if image_shape is None:
            raise ValueError("image_shape is required")
        if centers is None:
            return set(), None

        h, w = image_shape
        grid_rows, grid_cols = self._ensure_tile_grid(image_shape)
        tile_size = self._tile_size

        outer = self.get_outer_points(centers)
        if not outer:
            return set(), (grid_rows, grid_cols)

        poly = np.asarray(outer, dtype=np.int32).reshape(-1, 1, 2)
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask, [poly], 1)

        tiles = set()
        for row in range(grid_rows):
            y0 = row * tile_size
            y1 = min((row + 1) * tile_size, h)
            for col in range(grid_cols):
                x0 = col * tile_size
                x1 = min((col + 1) * tile_size, w)
                if np.any(mask[y0:y1, x0:x1]):
                    tiles.add((row, col))

        return tiles, (grid_rows, grid_cols)

    def _update_overlay(self, image_shape, tiles):
        if image_shape is None:
            raise ValueError("image_shape is required")
        if not tiles:
            return

        self._ensure_tile_grid(image_shape)
        for row, col in tiles:
            self._tile_counts[row, col] += 1

    def create_overlay(self):
        if self._tile_counts is None:
            return None

        grid_rows, grid_cols = self._tile_counts.shape
        overlay = np.zeros((grid_rows, grid_cols, 3), dtype=np.uint8)
        for row in range(grid_rows):
            for col in range(grid_cols):
                count = int(self._tile_counts[row, col])
                t = min(count, 10) / 10.0
                value = int(round((1.0 - t) * 255.0))
                color = cv2.applyColorMap(
                    np.array([[value]], dtype=np.uint8),
                    cv2.COLORMAP_JET,
                )[0, 0]
                overlay[row, col] = color

        return overlay

    def draw_detected_points(self, frame, centers, color=(0, 255, 0)):
        if frame is None:
            raise ValueError("frame is required")
        if centers is None:
            return frame

        pts = np.asarray(centers, dtype=np.float32)
        if pts.ndim == 3 and pts.shape[1:] == (1, 2):
            pts = pts.reshape(-1, 2)
        elif pts.ndim != 2 or pts.shape[1] != 2:
            raise ValueError("centers must be a Nx2 array or Nx1x2 array")

        annotated = frame.copy()
        for idx, (x, y) in enumerate(pts):
            cx, cy = int(round(x)), int(round(y))
            cv2.circle(annotated, (cx, cy), 4, color, -1)
            cv2.putText(
                annotated,
                str(idx),
                (cx + 5, cy - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                color,
                1,
                cv2.LINE_AA,
            )

        return annotated

    def draw_overlay(self, frame, tile_counts, alpha=0.5, max_count=10):
        if frame is None:
            raise ValueError("frame is required")
        if tile_counts is None:
            return frame

        counts = np.asarray(tile_counts)
        if counts.ndim != 2:
            raise ValueError("tile_counts must be a 2D array")

        grid_rows, grid_cols = counts.shape
        overlay = np.zeros((grid_rows, grid_cols, 3), dtype=np.uint8)
        for row in range(grid_rows):
            for col in range(grid_cols):
                count = int(counts[row, col])
                t = min(count, max_count) / float(max_count)
                value = int(round((1.0 - t) * 255.0))
                color = cv2.applyColorMap(
                    np.array([[value]], dtype=np.uint8),
                    cv2.COLORMAP_JET,
                )[0, 0]
                overlay[row, col] = color

        overlay_up = cv2.resize(
            overlay,
            (frame.shape[1], frame.shape[0]),
            interpolation=cv2.INTER_NEAREST,
        )
        return cv2.addWeighted(frame, 1.0 - alpha, overlay_up, alpha, 0)

    def get_tile_overlap_count(self):
        if self._tile_counts is None:
            return None
        return self._tile_counts.copy()

    def get_registered_frame_count(self):
        return len(self._objpoints)

    def is_executing(self):
        return bool(self._executing)

    def reset_registered_grids(self):
        """Clear all registered grid detections and related state."""
        if self._executing:
            raise RuntimeError("Calibration execution in progress")
        self._objpoints = []
        self._imgpoints = []
        self._last_size = None
        self._tile_counts = None
        self._tile_grid = None
        self._overlap_history = []
        self._overlap_history_set = set()
        self._feature_history = []
        self._feature_key_set = set()
        self._feature_key_history = []
        self.result = None

    def reset_calibration_data(self):
        self.reset_registered_grids()

    def _ensure_similarity_state(self):
        if not hasattr(self, "_feature_history"):
            self._feature_history = []
        if not hasattr(self, "_feature_key_set"):
            self._feature_key_set = set()
        if not hasattr(self, "_feature_key_history"):
            self._feature_key_history = []
        if not hasattr(self, "_feature_history_limit"):
            self._feature_history_limit = 300

        # Similarity thresholds (tune if needed)
        # Smaller -> stricter rejection
        if not hasattr(self, "_similarity_dist_thresh"):
            self._similarity_dist_thresh = 0.08
        if not hasattr(self, "_similarity_key_bins"):
            # Quantization bins for fast duplicate rejection
            self._similarity_key_bins = {
                "c": 24,   # center bins per axis
                "s": 24,   # scale bins (log scale)
                "a": 18,   # aspect bins (log aspect)
                "ang": 24, # angle bins over [-pi, pi)
            }

    def _compute_grid_feature(self, centers, image_shape):
        pts = np.asarray(centers, dtype=np.float32)
        if pts.ndim == 3 and pts.shape[1:] == (1, 2):
            pts = pts.reshape(-1, 2)
        if pts.ndim != 2 or pts.shape[1] != 2:
            raise ValueError("centers must be a Nx2 array or Nx1x2 array")

        h, w = image_shape
        if w <= 0 or h <= 0:
            raise ValueError("invalid image_shape")

        # Center (normalized)
        mean = np.mean(pts, axis=0)
        cx = float(mean[0]) / float(w)
        cy = float(mean[1]) / float(h)

        # Bounding box for scale/aspect (normalized)
        min_xy = np.min(pts, axis=0)
        max_xy = np.max(pts, axis=0)
        bw = float(max_xy[0] - min_xy[0])
        bh = float(max_xy[1] - min_xy[1])

        # Reject degenerate boxes
        if bw <= 1e-6 or bh <= 1e-6:
            return None

        diag = np.sqrt(bw * bw + bh * bh)
        norm = float(min(w, h))
        scale = float(diag) / norm
        if scale <= 1e-9:
            return None

        aspect = bw / bh
        if aspect <= 1e-9:
            return None

        # PCA angle (principal axis)
        # Center points for PCA
        X = pts - mean.reshape(1, 2)
        cov = (X.T @ X) / max(1, (X.shape[0] - 1))
        evals, evecs = np.linalg.eigh(cov)
        # largest eigenvector
        v = evecs[:, int(np.argmax(evals))]
        angle = float(np.arctan2(v[1], v[0]))  # [-pi, pi)

        # Log-space for scale/aspect to stabilize
        ls = float(np.log(scale))
        la = float(np.log(aspect))

        # Feature vector
        # cx, cy in [0,1], ls/ la unbounded but typically small
        return np.array([cx, cy, ls, la, angle], dtype=np.float32)

    def _feature_distance(self, f1, f2):
        # Weighted distance with angle wrap-around
        # f = [cx, cy, ls, la, angle]
        dcx = float(f1[0] - f2[0])
        dcy = float(f1[1] - f2[1])
        dls = float(f1[2] - f2[2])
        dla = float(f1[3] - f2[3])

        a1 = float(f1[4])
        a2 = float(f2[4])
        da = a1 - a2
        # wrap to [-pi, pi]
        da = (da + np.pi) % (2.0 * np.pi) - np.pi

        # Weights (tune if needed)
        wc = 1.0
        ws = 0.7
        wa = 0.5
        wang = 0.4

        return np.sqrt(
            wc * (dcx * dcx + dcy * dcy)
            + ws * (dls * dls)
            + wa * (dla * dla)
            + wang * (da * da)
        )

    def _quantize_feature(self, f):
        bins = self._similarity_key_bins
        cb = int(bins["c"])
        sb = int(bins["s"])
        ab = int(bins["a"])
        angb = int(bins["ang"])

        # cx, cy in [0,1]
        qcx = int(np.clip(np.floor(f[0] * cb), 0, cb - 1))
        qcy = int(np.clip(np.floor(f[1] * cb), 0, cb - 1))

        # ls, la: clamp to reasonable range before binning
        # These ranges are pragmatic defaults; adjust if your setup differs a lot.
        ls = float(np.clip(f[2], -4.0, 2.0))   # scale about exp([-4,2]) ~ [0.018, 7.39]
        la = float(np.clip(f[3], -2.0, 2.0))   # aspect about exp([-2,2]) ~ [0.135, 7.39]

        # map to [0,1]
        ls01 = (ls - (-4.0)) / (2.0 - (-4.0))
        la01 = (la - (-2.0)) / (2.0 - (-2.0))

        qls = int(np.clip(np.floor(ls01 * sb), 0, sb - 1))
        qla = int(np.clip(np.floor(la01 * ab), 0, ab - 1))

        # angle in [-pi, pi) -> [0,1)
        ang = float(f[4])
        ang01 = (ang + np.pi) / (2.0 * np.pi)
        qang = int(np.clip(np.floor(ang01 * angb), 0, angb - 1))

        return (qcx, qcy, qls, qla, qang)

    def add_grid_points(self, grid_points, image_shape=None):
        """Add detected grid points.

        Returns True when accepted; otherwise returns False.
        """
        if grid_points is None:
            return False

        self._ensure_similarity_state()

        pts = np.asarray(grid_points, dtype=np.float32)
        if pts.ndim == 2 and pts.shape[1] == 2:
            centers = pts.reshape(-1, 1, 2)
        elif pts.ndim == 3 and pts.shape[1:] == (1, 2):
            centers = pts
        else:
            raise ValueError("grid_points must be a Nx2 array or Nx1x2 array")

        expected = self.rows * self.cols
        if centers.shape[0] != expected:
            raise ValueError("grid_points size does not match pattern size")

        if image_shape is None:
            if self._last_size is None:
                raise ValueError("image_shape is required when no previous image size exists")
            image_shape = (self._last_size[1], self._last_size[0])
        else:
            image_shape = tuple(image_shape)

        if len(image_shape) != 2:
            raise ValueError("image_shape must be (height, width)")

        h, w = image_shape
        self._last_size = (w, h)

        # Basic sanity: all points must be finite and not wildly out of bounds
        c2 = centers.reshape(-1, 2)
        if not np.isfinite(c2).all():
            return False
        if np.min(c2[:, 0]) < -0.25 * w or np.max(c2[:, 0]) > 1.25 * w:
            return False
        if np.min(c2[:, 1]) < -0.25 * h or np.max(c2[:, 1]) > 1.25 * h:
            return False

        # Existing tile-overlap based duplicate rejection
        tiles, _ = self._get_overlap_tiles(image_shape, centers)
        if not tiles:
            return False

        tiles_key = frozenset(tiles)
        if tiles_key in self._overlap_history_set:
            return False

        # New: feature-based similarity rejection
        feat = self._compute_grid_feature(centers, image_shape)
        if feat is None:
            return False

        feat_key = self._quantize_feature(feat)
        if feat_key in self._feature_key_set:
            return False

        # Compare with recent history for continuous distance
        # To keep runtime bounded, check only the last N features
        recent = self._feature_history[-120:] if len(self._feature_history) > 120 else self._feature_history
        for fprev in recent:
            d = self._feature_distance(feat, fprev)
            if d < float(self._similarity_dist_thresh):
                return False

        # Accept: update histories
        self._overlap_history.append(tiles_key)
        self._overlap_history_set.add(tiles_key)
        if len(self._overlap_history) > self._overlap_history_limit:
            oldest = self._overlap_history.pop(0)
            self._overlap_history_set.discard(oldest)

        self._feature_history.append(feat)
        self._feature_key_history.append(feat_key)
        self._feature_key_set.add(feat_key)

        if len(self._feature_history) > self._feature_history_limit:
            drop_n = len(self._feature_history) - self._feature_history_limit
            for _ in range(drop_n):
                self._feature_history.pop(0)
                old_key = self._feature_key_history.pop(0)
                self._feature_key_set.discard(old_key)

        self._objpoints.append(self._objp)
        self._imgpoints.append(centers)

        if len(self._objpoints) > self.max_samples:
            self._objpoints = self._objpoints[: self.max_samples]
            self._imgpoints = self._imgpoints[: self.max_samples]

        self._update_overlay(image_shape, tiles)

        return True

    def execute_calibration(self):
        if self._executing:
            raise RuntimeError("Calibration already running")
        self._executing = True
        used = len(self._objpoints)
        result = {
            "pattern": {"cols": self.cols, "rows": self.rows, "type": "asymmetric"},
            "detections_total": int(used),
            "image_size_wh": list(self._last_size) if self._last_size else None,
            "physical": {
                "col_pitch_mm": self.col_pitch_mm,
                "row_pitch_mm": self.row_pitch_mm,
            },
            "lens_type": self.lens_type,
        }
        try:
            if used >= self.min_samples and self._last_size is not None:
                crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_COUNT, 100, 1e-6)
                lens_type = self.lens_type

                if lens_type == "fisheye":
                    obj_f = [op.reshape(1, -1, 3).astype(np.float64) for op in self._objpoints]
                    img_f = [ip.reshape(1, -1, 2).astype(np.float64) for ip in self._imgpoints]
                    K = np.zeros((3, 3), dtype=np.float64)
                    D = np.zeros((4, 1), dtype=np.float64)
                    flags = (
                        cv2.fisheye.CALIB_RECOMPUTE_EXTRINSIC
                        | cv2.fisheye.CALIB_CHECK_COND
                        | cv2.fisheye.CALIB_FIX_SKEW
                    )
                    try:
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
                    except cv2.error as exc:
                        # Retry without CALIB_CHECK_COND to avoid hard failures on borderline frames.
                        flags = cv2.fisheye.CALIB_RECOMPUTE_EXTRINSIC | cv2.fisheye.CALIB_FIX_SKEW
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
                        result["calibration_warning"] = f"fisheye CALIB_CHECK_COND failed: {exc}"

                    newK = cv2.fisheye.estimateNewCameraMatrixForUndistortRectify(
                        K,
                        D,
                        self._last_size,
                        np.eye(3),
                        balance=0.0,
                    )

                    result.update(
                        {
                            "calibration_performed": True,
                            "calibration_model": "fisheye",
                            "rms": float(rms),
                            "K_fisheye": K.tolist(),
                            "D_fisheye": D.reshape(-1).tolist(),
                            "K_pinhole": newK.tolist(),
                            "dist_pinhole": [0.0, 0.0, 0.0, 0.0],
                        }
                    )
                elif lens_type == "pinhole":
                    # calibrateCamera expects a list of Nx3 and Nx2 point arrays (not 1xNx3)
                    obj_f = [op.reshape(-1, 3).astype(np.float32) for op in self._objpoints]
                    img_f = [ip.reshape(-1, 2).astype(np.float32) for ip in self._imgpoints]
                    flags = 0
                    rms, K, dist, rvecs, tvecs = cv2.calibrateCamera(
                        obj_f,
                        img_f,
                        self._last_size,
                        None,
                        None,
                        flags=flags,
                        criteria=crit,
                    )

                    result.update(
                        {
                            "calibration_performed": True,
                            "calibration_model": "pinhole",
                            "rms": float(rms),
                            "K_pinhole": K.tolist(),
                            "dist_pinhole": dist.reshape(-1).tolist(),
                        }
                    )

                self.result = result
                return True

            result.update(
                {
                    "calibration_performed": False,
                    "reason": f"detections {used} < min_samples {self.min_samples}",
                }
            )

            self.result = result
            return False
        finally:
            self._executing = False

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

