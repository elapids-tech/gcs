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
const BIN_THRESHOLD_DEFAULT = 128;
const DOT_AREA_MIN_DEFAULT = 4;
const DOT_AREA_MAX_DEFAULT = 200;
const INCLUDE_GAIN_DEFAULT = 3.2;

const CAMERA_SPECS: Record<CameraControlKey, CameraControlSpec> = {
  brightness: { apiName: "brightness", label: "brightness", min: -64, max: 64, step: 1, def: 0 },
  contrast: { apiName: "contrast", label: "contrast", min: 0, max: 95, step: 1, def: 34 },
  saturation: { apiName: "saturation", label: "saturation", min: 0, max: 100, step: 1, def: 32 },
  hue: { apiName: "hue", label: "hue", min: -2000, max: 2000, step: 1, def: 0 },
  gamma: { apiName: "gamma", label: "gamma", min: 100, max: 300, step: 1, def: 150 },
  gain: { apiName: "gain", label: "gain", min: 0, max: 255, step: 1, def: 32 },
  exposure_time_absolute: {
    apiName: "exposure-time-absolute",
    label: "exposure_time_absolute",
    min: 1,
    max: 10000,
    step: 1,
    def: 20,
  },
  white_balance_temperature: {
    apiName: "white-balance-temperature",
    label: "white_balance_temperature",
    min: 2800,
    max: 6500,
    step: 1,
    def: 4600,
  },
  sharpness: { apiName: "sharpness", label: "sharpness", min: 1, max: 100, step: 1, def: 28 },
};

const ParameterSetter: React.FC = () => {
  const [threshold, setThreshold] = useState<number>(BIN_THRESHOLD_DEFAULT);
  const [thresholdOpen, setThresholdOpen] = useState<boolean>(true);
  const [cameraSettingsOpen, setCameraSettingsOpen] = useState<boolean>(true);
  const [landmarkSettingsOpen, setLandmarkSettingsOpen] = useState<boolean>(true);

  const [dotAreaMin, setDotAreaMin] = useState<number>(DOT_AREA_MIN_DEFAULT);
  const [dotAreaMax, setDotAreaMax] = useState<number>(DOT_AREA_MAX_DEFAULT);
  const [includeGain, setIncludeGain] = useState<number>(INCLUDE_GAIN_DEFAULT);

  const [camera, setCamera] = useState<CameraControlsState>({
    brightness: 0,
    contrast: 34,
    saturation: 32,
    hue: 0,
    gamma: 150,
    gain: 32,
    white_balance_temperature: 4600,
    sharpness: 28,
    exposure_time_absolute: 20,

    white_balance_automatic: 0,
    auto_exposure: 1,
  });

  // Debounce + in-flight + pending (per key)
  const debounceTimersRef = useRef<Record<string, number | undefined>>({});
  const inFlightRef = useRef<Record<string, boolean | undefined>>({});
  const pendingRef = useRef<Record<string, number | undefined>>({});

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

  return (
    <div>
      <h3>Image Processing Parameters</h3>

      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <h4 style={{ margin: 0 }}>Binary Threshold</h4>
        <button type="button" onClick={() => setThresholdOpen((v) => !v)}>
          {thresholdOpen ? "Hide" : "Show"}
        </button>
      </div>

      {thresholdOpen && (
        <div style={{ border: "1px solid #ccc", padding: 12, borderRadius: 8, marginTop: 8 }}>
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

      <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 16 }}>
        <h4 style={{ margin: 0 }}>Camera Settings</h4>
        <button type="button" onClick={() => setCameraSettingsOpen((v) => !v)}>
          {cameraSettingsOpen ? "Hide" : "Show"}
        </button>
      </div>

      {cameraSettingsOpen && (
        <div style={{ border: "1px solid #ccc", padding: 12, borderRadius: 8, marginTop: 8 }}>
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

      <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 16 }}>
        <h4 style={{ margin: 0 }}>Landmark Detection Parameters</h4>
        <button type="button" onClick={() => setLandmarkSettingsOpen((v) => !v)}>
          {landmarkSettingsOpen ? "Hide" : "Show"}
        </button>
      </div>

      {landmarkSettingsOpen && (
        <div style={{ border: "1px solid #ccc", padding: 12, borderRadius: 8, marginTop: 8 }}>
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
              <button
                type="button"
                onClick={() => setIncludeGain(INCLUDE_GAIN_DEFAULT)}
              >
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
  );
};

export default ParameterSetter;
