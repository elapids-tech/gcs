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

const DEBOUNCE_MS = 250;

const ParameterSetter: React.FC = () => {
  const [threshold, setThreshold] = useState<number>(128);
  const [thresholdOpen, setThresholdOpen] = useState<boolean>(true);
  const [cameraSettingsOpen, setCameraSettingsOpen] = useState<boolean>(true);

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
    fetch("http://localhost:8003/config-mode/get-bin-threshold")
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
    await fetch(`http://localhost:8003/config-mode/set-bin-threshold?threshold=${value}`, {
      method: "POST",
    });
  };

  const postCameraControl = async (key: string, value: number) => {
    await fetch(
      `http://localhost:8003/config-mode/set-camera-control?name=${encodeURIComponent(key)}&value=${value}`,
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

  // ---- Binary threshold slider ----
  const handleThresholdRangeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setThreshold(Number(e.target.value));
  };

  const handleThresholdRangeCommit = (e: React.SyntheticEvent<HTMLInputElement>) => {
    const value = Number((e.currentTarget as HTMLInputElement).value);
    scheduleSend("bin_threshold", value, postBinThreshold);
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
      scheduleSend(`camera:${key}`, value, (v) => postCameraControl(String(key), v));
    };

  const handleCameraNumberChange =
    (key: CameraControlKey) => (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = Number(e.target.value);
      setCameraValue(key, value);
      postCameraControl(String(key), value).catch((err) => console.warn("camera control送信失敗:", err));
    };

  const renderSlider = (
    key: CameraControlKey,
    label: string,
    min: number,
    max: number,
    step: number,
    def: number
  ) => {
    const value = camera[key];

    return (
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontFamily: "monospace", marginBottom: 6 }}>
          {label}: {value} (min={min} max={max} step={step} default={def})
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8 }}>
          <input
            type="number"
            min={min}
            max={max}
            step={step}
            value={value}
            onChange={handleCameraNumberChange(key)}
            style={{ width: 140 }}
          />
          <button
            type="button"
            onClick={() => {
              setCameraValue(key, def);
              postCameraControl(String(key), def).catch((err) => console.warn("camera control送信失敗:", err));
            }}
          >
            Default
          </button>
        </div>

        <input
          type="range"
          min={min}
          max={max}
          step={step}
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
          <div style={{ fontFamily: "monospace", marginBottom: 8 }}>
            -1 = disables binary thresholding.
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
          {renderSlider("brightness", "brightness", -64, 64, 1, 0)}
          {renderSlider("contrast", "contrast", 0, 95, 1, 34)}
          {renderSlider("saturation", "saturation", 0, 100, 1, 32)}
          {renderSlider("hue", "hue", -2000, 2000, 1, 0)}
          {renderSlider("gamma", "gamma", 100, 300, 1, 150)}
          {renderSlider("gain", "gain", 0, 255, 1, 32)}
          {renderSlider("exposure_time_absolute", "exposure_time_absolute", 1, 10000, 1, 20)}
          {renderSlider("white_balance_temperature", "white_balance_temperature", 2800, 6500, 1, 4600)}
          {renderSlider("sharpness", "sharpness", 1, 100, 1, 28)}
        </div>
      )}
    </div>
  );
};

export default ParameterSetter;
