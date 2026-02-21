import os
import cv2
from datetime import datetime


class VideoRecorder:
    def __init__(self, output_dir="idls_app/backend/recordings"):
        self.output_dir = output_dir
        self.video_writer = None
        self.is_recording_flag = False
        self.current_filename = None  # full path

    def is_recording(self):
        return self.is_recording_flag

    def _generate_filepath(self) -> str:
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        base = ts
        ext = ".mp4"
        path = os.path.join(self.output_dir, base + ext)
        suffix = 1
        while os.path.exists(path):
            path = os.path.join(self.output_dir, f"{base}_{suffix}" + ext)
            suffix += 1
        return path

    def start(self) -> dict:
        if self.is_recording_flag:
            return {
                "status": "already_recording",
                "filename": os.path.basename(self.current_filename) if self.current_filename else None,
            }
        os.makedirs(self.output_dir, exist_ok=True)
        self.current_filename = self._generate_filepath()
        self.video_writer = None  # lazy init on first frame
        self.is_recording_flag = True
        return {"status": "started", "filename": os.path.basename(self.current_filename)}

    def update(self, frame) -> None:
        if not self.is_recording_flag or self.current_filename is None:
            return
        if self.video_writer is None:
            h, w = frame.shape[:2]
            is_color = frame.ndim == 3
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            self.video_writer = cv2.VideoWriter(
                self.current_filename, fourcc, 15.0, (w, h), isColor=is_color
            )
        if self.video_writer.isOpened():
            self.video_writer.write(frame)

    def stop(self) -> dict:
        if not self.is_recording_flag:
            return {"status": "not_recording", "filename": None}
        filename = os.path.basename(self.current_filename) if self.current_filename else None
        if self.video_writer is not None:
            self.video_writer.release()
            self.video_writer = None
        self.is_recording_flag = False
        self.current_filename = None
        return {"status": "stopped", "filename": filename}

    def get_current_filename(self) -> str | None:
        if self.is_recording_flag and self.current_filename:
            return os.path.basename(self.current_filename)
        return None

    def get_video_file_name_list(self) -> list[str]:
        if not os.path.exists(self.output_dir):
            return []
        current = self.get_current_filename()
        files = [
            f for f in os.listdir(self.output_dir)
            if f.endswith(".mp4") and f != current
        ]
        return sorted(files)
