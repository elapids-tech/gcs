import React, { useEffect, useRef, useState } from "react";

type CameraControlKey =
  | "brightness"
  | "contrast"
  | "saturation"
  | "hue"
  | "gamma"
  | "gain"
  | "white_balance_temperature"
  | "sharpness"
  | "exposure_time_absolute";

type CameraControlsState = Record<CameraControlKey, number> & {
  white_balance_automatic: number; // fixed 0
  auto_exposure: number; // fixed manual
};

type CameraControlSpec = {
  apiName: string; // not use underscore
  label: string;   // display label
  min: number;
  max: number;
  step: number;
  def: number;
};

const API_BASE_URL = "http://localhost:8003";
const DEBOUNCE_MS = 250;
const BIN_THRESHOLD_DEFAULT = 70;
const DOT_AREA_MIN_DEFAULT = 4;
const DOT_AREA_MAX_DEFAULT = 200;
const INCLUDE_GAIN_DEFAULT = 3.2;
const SECTION_MAX_WIDTH = 360;
const CALIBRATION_POLL_MS = 2000;

const CAMERA_SPECS: Record<CameraControlKey, CameraControlSpec> = {
  brightness: { apiName: "brightness", label: "brightness", min: -64, max: 64, step: 1, def: 0 },
  contrast: { apiName: "contrast", label: "contrast", min: 0, max: 95, step: 1, def: 50 },
  saturation: { apiName: "saturation", label: "saturation", min: 0, max: 100, step: 1, def: 32 },
  hue: { apiName: "hue", label: "hue", min: -2000, max: 2000, step: 1, def: 0 },
  gamma: { apiName: "gamma", label: "gamma", min: 100, max: 300, step: 1, def: 140 },
  gain: { apiName: "gain", label: "gain", min: 0, max: 255, step: 1, def: 190 },
  exposure_time_absolute: {
    apiName: "exposure-time-absolute",
    label: "exposure_time_absolute",
    min: 1,
    max: 10000,
    step: 1,
    def: 5,
  },
  white_balance_temperature: {
    apiName: "white-balance-temperature",
    label: "white_balance_temperature",
    min: 2800,
    max: 6500,
    step: 1,
    def: 4600,
  },
  sharpness: { apiName: "sharpness", label: "sharpness", min: 1, max: 100, step: 1, def: 70 },
};

const ParameterSetter: React.FC = () => {
  const [threshold, setThreshold] = useState<number>(BIN_THRESHOLD_DEFAULT);
  const [thresholdOpen, setThresholdOpen] = useState<boolean>(false);
  const [cameraSettingsOpen, setCameraSettingsOpen] = useState<boolean>(false);
  const [cameraCalibrationOpen, setCameraCalibrationOpen] = useState<boolean>(false);
  const [landmarkSettingsOpen, setLandmarkSettingsOpen] = useState<boolean>(false);
  const [hoveredSection, setHoveredSection] = useState<"threshold" | "camera" | "calibration" | "landmark" | "recording" | null>(null);
  const [recording, setRecording] = useState<boolean>(false);
  const [recordingOpen, setRecordingOpen] = useState<boolean>(false);
  const [recordingFiles, setRecordingFiles] = useState<string[]>([]);
  const [recordingInProgress, setRecordingInProgress] = useState<string | null>(null);
  const [selectedRecordingFile, setSelectedRecordingFile] = useState<string>("");
  const [calibrationCamera, setCalibrationCamera] = useState<string>("0");
  const [calibrationLensType, setCalibrationLensType] = useState<string>("pinhole");
  const [calibrationRunningByCamera, setCalibrationRunningByCamera] = useState<Record<number, boolean>>({ 0: false, 1: false });
  const [executeRunningByCamera, setExecuteRunningByCamera] = useState<Record<number, boolean>>({ 0: false, 1: false });
  const [executeResultByCamera, setExecuteResultByCamera] = useState<Record<number, boolean>>({ 0: false, 1: false });
  const [executeErrorByCamera, setExecuteErrorByCamera] = useState<Record<number, string | null>>({ 0: null, 1: null });
  const [registeredCounts, setRegisteredCounts] = useState<Record<number, number>>({ 0: 0, 1: 0 });
  const calibrationRunningRef = useRef<Record<number, boolean>>({ 0: false, 1: false });

  const [dotAreaMin, setDotAreaMin] = useState<number>(DOT_AREA_MIN_DEFAULT);
  const [dotAreaMax, setDotAreaMax] = useState<number>(DOT_AREA_MAX_DEFAULT);
  const [includeGain, setIncludeGain] = useState<number>(INCLUDE_GAIN_DEFAULT);

  const [camera, setCamera] = useState<CameraControlsState>({
    brightness: 0,
    contrast: 50,
    saturation: 32,
    hue: 0,
    gamma: 140,
    gain: 190,
    white_balance_temperature: 4600,
    sharpness: 70,
    exposure_time_absolute: 5,

    white_balance_automatic: 0,
    auto_exposure: 1,
  });

  // Debounce + in-flight + pending (per key)
  const debounceTimersRef = useRef<Record<string, number | undefined>>({});
  const inFlightRef = useRef<Record<string, boolean | undefined>>({});
  const pendingRef = useRef<Record<string, number | undefined>>({});

  const selectedCamera = Number(calibrationCamera);
  const calibrationRunning = calibrationRunningByCamera[selectedCamera] ?? false;
  const executeRunning = executeRunningByCamera[selectedCamera] ?? false;
  const executeResultAvailable = executeResultByCamera[selectedCamera] ?? false;
  const executeError = executeErrorByCamera[selectedCamera] ?? null;
  const registeredCount = registeredCounts[selectedCamera] ?? 0;

  useEffect(() => {
    fetch(`${API_BASE_URL}/config-mode/get-bin-threshold`)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch threshold");
        return res.json();
      })
      .then((data) => {
        if (typeof data.bin_threshold === "number") {
          setThreshold(data.bin_threshold);
        }
      })
      .catch((e) => console.warn("しきい値の取得失敗:", e));
  }, []);

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8003/ws");

    ws.onmessage = (event) => {
      if (typeof event.data !== "string") {
        return;
      }

      try {
        const data = JSON.parse(event.data);
        if (data?.key !== "cameraCalibrationUpdate" || !data.value) {
          return;
        }

        const cameraId = Number(data.value.camera);
        const count = Number(data.value.registeredCount);
        const running = Boolean(data.value.running);

        if (!Number.isNaN(cameraId) && !Number.isNaN(count)) {
          setRegisteredCounts((prev) => ({ ...prev, [cameraId]: count }));
          setCalibrationRunningByCamera((prev) => ({ ...prev, [cameraId]: running }));
        }
      } catch (err) {
        console.warn("calibration websocket parse error:", err);
      }
    };

    ws.onerror = (err) => {
      console.warn("calibration websocket error:", err);
    };

    return () => {
      ws.close();
    };
  }, []);

  const startCalibration = async (cameraId: string) => {
    await fetch(`${API_BASE_URL}/config-mode/camera-calibration/start?camera=${encodeURIComponent(cameraId)}`,
      { method: "POST" }
    );
  };

  const stopCalibration = async () => {
    await fetch(`${API_BASE_URL}/config-mode/camera-calibration/stop`, { method: "POST" });
  };

  const executeCalibration = async () => {
    const res = await fetch(
      `${API_BASE_URL}/config-mode/camera-calibration/execute-calibration?camera=${encodeURIComponent(calibrationCamera)}&lens_type=${encodeURIComponent(calibrationLensType)}`,
      { method: "POST" }
    );
    if (!res.ok) {
      const message = await res.text();
      console.warn("execute-calibration failed:", message);
      setExecuteRunningByCamera((prev) => ({ ...prev, [selectedCamera]: false }));
      setExecuteErrorByCamera((prev) => ({ ...prev, [selectedCamera]: message }));
      return;
    }
    setExecuteRunningByCamera((prev) => ({ ...prev, [selectedCamera]: true }));
    setExecuteErrorByCamera((prev) => ({ ...prev, [selectedCamera]: null }));
  };

  const downloadCalibration = async () => {
    const res = await fetch(
      `${API_BASE_URL}/config-mode/camera-calibration/download?camera=${encodeURIComponent(calibrationCamera)}`
    );
    if (!res.ok) {
      let message = "Calibration result not found.";
      try {
        const data = await res.json();
        if (data?.message) {
          message = String(data.message);
        }
      } catch (err) {
        // ignore parse errors and fall back to default message
      }
      window.alert(message);
      return;
    }

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const filename = `camera_${calibrationCamera}_calibration.json`;
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  const saveCalibrationToDrone = async () => {
    // Mock only: backend wiring will be added later.
    console.warn("save to drone is not wired yet");
  };

  const startRecording = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/recording/start`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        setRecordingInProgress(data.filename ?? null);
        setRecording(true);
      } else {
        console.warn("recording start failed");
      }
    } catch (e) {
      console.warn("recording start error:", e);
    }
  };

  const stopRecording = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/recording/stop`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        setRecordingInProgress(null);
        setRecording(false);
        if (Array.isArray(data.files)) {
          setRecordingFiles(data.files);
          if (data.filename && !selectedRecordingFile) {
            setSelectedRecordingFile(data.filename);
          }
        }
      } else {
        console.warn("recording stop failed");
      }
    } catch (e) {
      console.warn("recording stop error:", e);
    }
  };

  const downloadRecordingFile = async (fileName: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/recording/download/${encodeURIComponent(fileName)}`);
      if (!res.ok) {
        window.alert("Download failed.");
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.warn("download error:", e);
      window.alert("Download failed.");
    }
  };

  const resetCalibration = async () => {
    const res = await fetch(
      `${API_BASE_URL}/config-mode/camera-calibration/reset-calibration-data?camera=${encodeURIComponent(calibrationCamera)}`,
      { method: "POST" }
    );
    if (!res.ok) {
      const message = await res.text();
      console.warn("reset-calibration-data failed:", message);
      window.alert(message || "Reset failed.");
      return;
    }
    const data = await res.json();
    const count = Number(data?.registeredCount);
    if (!Number.isNaN(count)) {
      setRegisteredCounts((prev) => ({ ...prev, [selectedCamera]: count }));
    }
    setExecuteResultByCamera((prev) => ({ ...prev, [selectedCamera]: false }));
    setExecuteErrorByCamera((prev) => ({ ...prev, [selectedCamera]: null }));
  };

  const getCalibrationStatus = async () => {
    const res = await fetch(`${API_BASE_URL}/config-mode/camera-calibration/status`);
    if (!res.ok) {
      throw new Error("Failed to fetch calibration status");
    }
    return res.json();
  };

  const getExecuteStatus = async (cameraId: number) => {
    const res = await fetch(
      `${API_BASE_URL}/config-mode/camera-calibration/execute-status?camera=${encodeURIComponent(String(cameraId))}`
    );
    if (!res.ok) {
      throw new Error("Failed to fetch execute status");
    }
    return res.json();
  };

  useEffect(() => {
    calibrationRunningRef.current = calibrationRunningByCamera;
  }, [calibrationRunningByCamera]);

  useEffect(() => {
    const sync = async () => {
      try {
        const results = await Promise.all([getExecuteStatus(0), getExecuteStatus(1)]);
        setExecuteRunningByCamera({
          0: Boolean(results[0]?.running),
          1: Boolean(results[1]?.running),
        });
        setExecuteResultByCamera({
          0: Boolean(results[0]?.result_available),
          1: Boolean(results[1]?.result_available),
        });
        setExecuteErrorByCamera({
          0: results[0]?.last_error ? String(results[0].last_error) : null,
          1: results[1]?.last_error ? String(results[1].last_error) : null,
        });
      } catch (err) {
        console.warn("execute status 取得失敗:", err);
      }
    };

    sync();
  }, []);

  useEffect(() => {
    const anyRunning = Object.values(calibrationRunningByCamera).some(Boolean);
    if (!anyRunning) {
      return undefined;
    }

    const timer = window.setInterval(() => {
      getCalibrationStatus().catch((err) => console.warn("calibration status 取得失敗:", err));
    }, CALIBRATION_POLL_MS);

    return () => {
      window.clearInterval(timer);
    };
  }, [calibrationRunningByCamera]);

  useEffect(() => {
    const anyExecuting = Object.values(executeRunningByCamera).some(Boolean);
    if (!anyExecuting) {
      return undefined;
    }

    const timer = window.setInterval(() => {
      Promise.all([getExecuteStatus(0), getExecuteStatus(1)])
        .then((results) => {
          setExecuteRunningByCamera({
            0: Boolean(results[0]?.running),
            1: Boolean(results[1]?.running),
          });
          setExecuteResultByCamera({
            0: Boolean(results[0]?.result_available),
            1: Boolean(results[1]?.result_available),
          });
          setExecuteErrorByCamera({
            0: results[0]?.last_error ? String(results[0].last_error) : null,
            1: results[1]?.last_error ? String(results[1].last_error) : null,
          });
        })
        .catch((err) => console.warn("execute status 取得失敗:", err));
    }, 1000);

    return () => {
      window.clearInterval(timer);
    };
  }, [executeRunningByCamera]);

  useEffect(() => {
    return () => {
      const anyRunning = Object.values(calibrationRunningRef.current).some(Boolean);
      if (anyRunning) {
        stopCalibration().catch((err) => console.warn("calibration stop 送信失敗:", err));
      }
    };
  }, []);

  useEffect(() => {
    const fetchList = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/recording/list`);
        if (res.ok) {
          const data = await res.json();
          setRecordingFiles(data.files ?? []);
          const inProgress = data.recording ?? null;
          setRecordingInProgress(inProgress);
          setRecording(!!inProgress);
        }
      } catch (e) {
        console.warn("recording list fetch failed:", e);
      }
    };
    fetchList();
    const timer = window.setInterval(fetchList, 2000);
    return () => window.clearInterval(timer);
  }, []);

  const postBinThreshold = async (value: number) => {
    await fetch(`${API_BASE_URL}/config-mode/set-bin-threshold?threshold=${value}`, {
      method: "POST",
    });
  };

  const postCameraControl = async (key: CameraControlKey, value: number) => {
    const apiName = CAMERA_SPECS[key].apiName;
    await fetch(
      `${API_BASE_URL}/config-mode/set-camera-control?name=${encodeURIComponent(apiName)}&value=${value}`,
      { method: "POST" }
    );
  };

  const clearTimer = (k: string) => {
    const t = debounceTimersRef.current[k];
    if (t !== undefined) {
      window.clearTimeout(t);
      debounceTimersRef.current[k] = undefined;
    }
  };

  const trySend = (k: string, sendFn: (value: number) => Promise<void>) => {
    if (inFlightRef.current[k]) {
      return;
    }
    const value = pendingRef.current[k];
    if (value === undefined) {
      return;
    }

    pendingRef.current[k] = undefined;
    inFlightRef.current[k] = true;

    sendFn(value)
      .catch((e) => console.warn("送信失敗:", e))
      .finally(() => {
        inFlightRef.current[k] = false;

        if (pendingRef.current[k] !== undefined) {
          clearTimer(k);
          debounceTimersRef.current[k] = window.setTimeout(() => {
            trySend(k, sendFn);
          }, 0);
        }
      });
  };

  const scheduleSend = (k: string, value: number, sendFn: (value: number) => Promise<void>) => {
    pendingRef.current[k] = value;
    clearTimer(k);
    debounceTimersRef.current[k] = window.setTimeout(() => {
      trySend(k, sendFn);
    }, DEBOUNCE_MS);
  };

  const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);
  const DOT_AREA_GAP = 1;
  const clampDotAreaMin = (value: number) => clamp(value, 4, Math.min(200 - DOT_AREA_GAP, dotAreaMax - DOT_AREA_GAP));
  const clampDotAreaMax = (value: number) => clamp(value, Math.max(4 + DOT_AREA_GAP, dotAreaMin + DOT_AREA_GAP), 200);

  // ---- Binary threshold slider ----
  const handleThresholdRangeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setThreshold(Number(e.target.value));
  };

  const handleThresholdRangeCommit = (e: React.SyntheticEvent<HTMLInputElement>) => {
    const value = Number((e.currentTarget as HTMLInputElement).value);
    scheduleSend("bin-threshold", value, postBinThreshold);
  };

  const handleThresholdNumberChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = Number(e.target.value);
    setThreshold(value);
    scheduleSend("bin-threshold", value, postBinThreshold);
  };

  // ---- Camera controls ----
  const setCameraValue = (key: keyof CameraControlsState, value: number) => {
    setCamera((prev) => ({ ...prev, [key]: value }));
  };

  const handleCameraRangeChange =
    (key: CameraControlKey) => (e: React.ChangeEvent<HTMLInputElement>) => {
      setCameraValue(key, Number(e.target.value));
    };

  const handleCameraRangeCommit =
    (key: CameraControlKey) => (e: React.SyntheticEvent<HTMLInputElement>) => {
      const value = Number((e.currentTarget as HTMLInputElement).value);
      scheduleSend(`camera:${key}`, value, (v) => postCameraControl(key, v));
    };

  const handleCameraNumberChange =
    (key: CameraControlKey) => (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = Number(e.target.value);
      setCameraValue(key, value);
      postCameraControl(key, value).catch((err) => console.warn("camera control送信失敗:", err));
    };

  const renderSlider = (key: CameraControlKey) => {
    const spec = CAMERA_SPECS[key];
    const value = camera[key];

    return (
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontFamily: "monospace", marginBottom: 6 }}>
          {spec.label}: {value} (min={spec.min} max={spec.max} step={spec.step} default={spec.def})
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8 }}>
          <input
            type="number"
            min={spec.min}
            max={spec.max}
            step={spec.step}
            value={value}
            onChange={handleCameraNumberChange(key)}
            style={{ width: 140 }}
          />
          <button
            type="button"
            onClick={() => {
              setCameraValue(key, spec.def);
              postCameraControl(key, spec.def).catch((err) => console.warn("camera control送信失敗:", err));
            }}
          >
            Default
          </button>
        </div>

        <input
          type="range"
          min={spec.min}
          max={spec.max}
          step={spec.step}
          value={value}
          onChange={handleCameraRangeChange(key)}
          onMouseUp={handleCameraRangeCommit(key)}
          onTouchEnd={handleCameraRangeCommit(key)}
          style={{ width: "100%" }}
        />
      </div>
    );
  };

  const sectionHeaderStyle: React.CSSProperties = {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "4px 6px",
    borderRadius: 6,
    cursor: "pointer",
    userSelect: "text",
  };

  const sectionBodyStyle: React.CSSProperties = {
    width: "100%",
    boxSizing: "border-box",
    border: "1px solid #ccc",
    padding: 12,
    borderRadius: 8,
    marginTop: 8,
  };

  const sectionBlockStyle: React.CSSProperties = {
    width: SECTION_MAX_WIDTH,
    maxWidth: SECTION_MAX_WIDTH,
    boxSizing: "border-box",
  };

  const chevronStyle = (open: boolean): React.CSSProperties => ({
    width: 12,
    height: 12,
    transition: "transform 120ms ease",
    transform: open ? "rotate(90deg)" : "rotate(0deg)",
  });

  return (
    <div>
      <h3>Image Processing Parameters</h3>

      <div style={{ ...sectionBlockStyle, marginTop: 12 }}>
        <div
          style={{
            ...sectionHeaderStyle,
            background: hoveredSection === "recording" ? "#f0f0f0" : "transparent",
          }}
          onClick={() => setRecordingOpen((v) => !v)}
          onMouseEnter={() => setHoveredSection("recording")}
          onMouseLeave={() => setHoveredSection(null)}
          role="button"
          tabIndex={0}
        >
          <svg style={chevronStyle(recordingOpen)} viewBox="0 0 16 16" aria-hidden="true">
            <path d="M6 4l4 4-4 4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <h4 style={{ margin: 0 }}>Recording</h4>
        </div>

        {recordingOpen && (
          <div style={sectionBodyStyle}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ fontFamily: "monospace", fontSize: 14 }}>Recording</div>
              <button
                type="button"
                onClick={() => (recording ? stopRecording() : startRecording())}
                style={{
                  width: 120,
                  height: 36,
                  padding: "6px 8px",
                  boxSizing: "border-box",
                  borderRadius: 6,
                  border: recording ? "1px solid #ff8080" : "1px solid #ccc",
                  background: recording ? "#ffb3b3" : "#fff",
                  color: "#000",
                  appearance: "none",
                  WebkitAppearance: "none",
                }}
              >
                {recording ? "Stop" : "Start"}
              </button>
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 12 }}>
              <select
                value={selectedRecordingFile}
                onChange={(e) => setSelectedRecordingFile(e.target.value)}
                style={{ width: 220 }}
              >
                {recordingInProgress && (
                  <option value="" disabled>
                    *{recordingInProgress}
                  </option>
                )}
                {recordingFiles.map((f) => (
                  <option key={f} value={f}>
                    {f}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => downloadRecordingFile(selectedRecordingFile)}
                disabled={!selectedRecordingFile}
                style={{ width: 100 }}
              >
                Download
              </button>
            </div>
          </div>
        )}
      </div>

      <div style={{ ...sectionBlockStyle, marginTop: 12 }}>
        <div
          style={{
            ...sectionHeaderStyle,
            background: hoveredSection === "threshold" ? "#f0f0f0" : "transparent",
          }}
          onClick={() => setThresholdOpen((v) => !v)}
          onMouseEnter={() => setHoveredSection("threshold")}
          onMouseLeave={() => setHoveredSection(null)}
          role="button"
          tabIndex={0}
        >
          <svg style={chevronStyle(thresholdOpen)} viewBox="0 0 16 16" aria-hidden="true">
            <path d="M6 4l4 4-4 4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <h4 style={{ margin: 0 }}>Binary Threshold</h4>
        </div>

        {thresholdOpen && (
          <div style={sectionBodyStyle}>
            <div style={{ fontFamily: "monospace", marginBottom: 6 }}>
              binary_threshold: {threshold === -1 ? "disabled" : threshold} (min=-1 max=255 step=1)
            </div>
            <div style={{ fontFamily: "monospace", marginBottom: 8 }}>-1 = disables binary thresholding.</div>
            <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8 }}>
              <input
                type="number"
                min={-1}
                max={255}
                step={1}
                value={threshold}
                onChange={handleThresholdNumberChange}
                style={{ width: 140 }}
              />
              <button
                type="button"
                onClick={() => {
                  setThreshold(BIN_THRESHOLD_DEFAULT);
                  scheduleSend("bin-threshold", BIN_THRESHOLD_DEFAULT, postBinThreshold);
                }}
              >
                Default
              </button>
            </div>
            <input
              type="range"
              min="-1"
              max="255"
              step="1"
              value={threshold}
              onChange={handleThresholdRangeChange}
              onMouseUp={handleThresholdRangeCommit}
              onTouchEnd={handleThresholdRangeCommit}
              style={{ width: "100%" }}
            />
          </div>
        )}
      </div>

      <div style={{ ...sectionBlockStyle, marginTop: 12 }}>
        <div
          style={{
            ...sectionHeaderStyle,
            background: hoveredSection === "camera" ? "#f0f0f0" : "transparent",
          }}
          onClick={() => setCameraSettingsOpen((v) => !v)}
          onMouseEnter={() => setHoveredSection("camera")}
          onMouseLeave={() => setHoveredSection(null)}
          role="button"
          tabIndex={0}
        >
          <svg style={chevronStyle(cameraSettingsOpen)} viewBox="0 0 16 16" aria-hidden="true">
            <path d="M6 4l4 4-4 4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <h4 style={{ margin: 0 }}>Camera Settings</h4>
        </div>

        {cameraSettingsOpen && (
          <div style={sectionBodyStyle}>
            {renderSlider("brightness")}
            {renderSlider("contrast")}
            {renderSlider("saturation")}
            {renderSlider("hue")}
            {renderSlider("gamma")}
            {renderSlider("gain")}
            {renderSlider("exposure_time_absolute")}
            {renderSlider("white_balance_temperature")}
            {renderSlider("sharpness")}
          </div>
        )}
      </div>

      <div style={{ ...sectionBlockStyle, marginTop: 12 }}>
        <div
          style={{
            ...sectionHeaderStyle,
            background: hoveredSection === "calibration" ? "#f0f0f0" : "transparent",
          }}
          onClick={() => setCameraCalibrationOpen((v) => !v)}
          onMouseEnter={() => setHoveredSection("calibration")}
          onMouseLeave={() => setHoveredSection(null)}
          role="button"
          tabIndex={0}
        >
          <svg style={chevronStyle(cameraCalibrationOpen)} viewBox="0 0 16 16" aria-hidden="true">
            <path d="M6 4l4 4-4 4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <h4 style={{ margin: 0 }}>Camera Calibration</h4>
        </div>

        {cameraCalibrationOpen && (
          <div style={sectionBodyStyle}>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "140px 1fr",
                rowGap: 10,
                columnGap: 12,
                alignItems: "center",
              }}
            >
              <div style={{ fontFamily: "monospace", fontSize: 12 }}>Camera Select</div>
              <select
                value={calibrationCamera}
                onChange={(e) => setCalibrationCamera(e.target.value)}
                disabled={calibrationRunning}
                style={{ width: 160 }}
              >
                <option value="0">camera 0</option>
                <option value="1">camera 1</option>
              </select>

              <div style={{ fontFamily: "monospace", fontSize: 12 }}>Lens Type</div>
              <select
                value={calibrationLensType}
                onChange={(e) => setCalibrationLensType(e.target.value)}
                disabled={executeRunning}
                style={{ width: 160 }}
              >
                <option value="fisheye">fisheye</option>
                <option value="pinhole">pinhole</option>
              </select>

              <div style={{ fontFamily: "monospace", fontSize: 12 }}>Grid Detection</div>
              <button
                type="button"
                onClick={() => {
                  if (calibrationRunning) {
                    stopCalibration().catch((err) => console.warn("calibration stop 送信失敗:", err));
                    setCalibrationRunningByCamera({ 0: false, 1: false });
                  } else {
                    startCalibration(calibrationCamera).catch((err) => console.warn("calibration start 送信失敗:", err));
                    setCalibrationRunningByCamera((prev) => ({
                      ...prev,
                      0: selectedCamera === 0,
                      1: selectedCamera === 1,
                    }));
                  }
                }}
                style={{ width: 160 }}
              >
                {calibrationRunning ? "Stop" : "Start"}
              </button>

              <div style={{ fontFamily: "monospace", fontSize: 12 }}>Registered Count</div>
              <div style={{ fontFamily: "monospace" }}>{registeredCount}</div>

              <div style={{ fontFamily: "monospace", fontSize: 12 }}>Calibration</div>
              <div style={{ display: "flex", gap: 8 }}>
                <button
                  type="button"
                  onClick={executeCalibration}
                  style={{ width: 160 }}
                  disabled={executeRunning}
                >
                  {executeRunning ? "Executing..." : "Execute"}
                </button>
              </div>
              <div style={{ fontFamily: "monospace", fontSize: 12 }}>Execute Status</div>
              <div style={{ fontFamily: "monospace" }}>
                {executeRunning ? "running" : executeResultAvailable ? "ready" : "no result"}
                {executeError ? ` (error: ${executeError})` : ""}
              </div>

              <div style={{ fontFamily: "monospace", fontSize: 12 }}>Result download</div>
              <button
                type="button"
                onClick={() =>
                  downloadCalibration().catch((err) => {
                    console.warn("calibration download 失敗:", err);
                    window.alert("Calibration download failed.");
                  })
                }
                style={{ width: 160 }}
                disabled={!executeResultAvailable || executeRunning}
              >
                Download
              </button>

              <div style={{ fontFamily: "monospace", fontSize: 12 }}>Save to drone</div>
              <button type="button" onClick={saveCalibrationToDrone} style={{ width: 160 }}>
                Save
              </button>

              <div style={{ gridColumn: "1 / -1", borderTop: "1px solid #ccc", marginTop: 6, paddingTop: 10 }} />

              <div />
              <button
                type="button"
                onClick={resetCalibration}
                style={{ width: 160 }}
                disabled={executeRunning}
              >
                Reset
              </button>
            </div>
          </div>
        )}
      </div>

      <div style={{ ...sectionBlockStyle, marginTop: 12 }}>
        <div
          style={{
            ...sectionHeaderStyle,
            background: hoveredSection === "landmark" ? "#f0f0f0" : "transparent",
          }}
          onClick={() => setLandmarkSettingsOpen((v) => !v)}
          onMouseEnter={() => setHoveredSection("landmark")}
          onMouseLeave={() => setHoveredSection(null)}
          role="button"
          tabIndex={0}
        >
          <svg style={chevronStyle(landmarkSettingsOpen)} viewBox="0 0 16 16" aria-hidden="true">
            <path d="M6 4l4 4-4 4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <h4 style={{ margin: 0 }}>Landmark Detection Parameters</h4>
        </div>

        {landmarkSettingsOpen && (
          <div style={sectionBodyStyle}>
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontFamily: "monospace", marginBottom: 6 }}>
                dot_area (min={dotAreaMin.toFixed(1)} max={dotAreaMax.toFixed(1)})
              </div>
              <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8 }}>
                <input
                  type="number"
                  min={4}
                  max={200}
                  step={0.1}
                  value={dotAreaMin}
                  onChange={(e) => setDotAreaMin(clampDotAreaMin(Number(e.target.value)))}
                  style={{ width: 140 }}
                />
                <input
                  type="number"
                  min={4}
                  max={200}
                  step={0.1}
                  value={dotAreaMax}
                  onChange={(e) => setDotAreaMax(clampDotAreaMax(Number(e.target.value)))}
                  style={{ width: 140 }}
                />
                <button
                  type="button"
                  onClick={() => {
                    setDotAreaMin(DOT_AREA_MIN_DEFAULT);
                    setDotAreaMax(DOT_AREA_MAX_DEFAULT);
                  }}
                >
                  Default
                </button>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <input
                  type="range"
                  min="4"
                  max="200"
                  step="0.1"
                  value={dotAreaMin}
                  onChange={(e) => setDotAreaMin(clampDotAreaMin(Number(e.target.value)))}
                  style={{ width: "100%" }}
                />
                <input
                  type="range"
                  min="4"
                  max="200"
                  step="0.1"
                  value={dotAreaMax}
                  onChange={(e) => setDotAreaMax(clampDotAreaMax(Number(e.target.value)))}
                  style={{ width: "100%" }}
                />
              </div>
            </div>

            <div>
              <div style={{ fontFamily: "monospace", marginBottom: 6 }}>
                include_gain: {includeGain.toFixed(1)} (min=2.0 max=10.0)
              </div>
              <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8 }}>
                <input
                  type="number"
                  min={2}
                  max={10}
                  step={0.1}
                  value={includeGain}
                  onChange={(e) => setIncludeGain(Number(e.target.value))}
                  style={{ width: 140 }}
                />
                <button type="button" onClick={() => setIncludeGain(INCLUDE_GAIN_DEFAULT)}>
                  Default
                </button>
              </div>
              <input
                type="range"
                min="2"
                max="10"
                step="0.1"
                value={includeGain}
                onChange={(e) => setIncludeGain(Number(e.target.value))}
                style={{ width: "100%" }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ParameterSetter;
