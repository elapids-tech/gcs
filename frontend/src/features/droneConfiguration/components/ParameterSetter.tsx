import React, { useRef, useState } from "react";

export interface ParameterSetterProps {
  initialThreshold: number;
  onSave: (value: number) => void;
}

const ParameterSetter: React.FC<ParameterSetterProps> = ({
  initialThreshold,
  onSave,
}) => {
  const [threshold, setThreshold] = useState(initialThreshold);
  const debounceRef = useRef<number | null>(null);

  const sendParameter = (value: number) => {
    fetch("http://localhost:8003/config-mode/parameter", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ threshold: value }),
    }).catch((err) => console.error("ParameterSendAPI error:", err));
  };

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = Number(e.target.value);
    setThreshold(v);
    if (debounceRef.current) window.clearTimeout(debounceRef.current);
    debounceRef.current = window.setTimeout(() => sendParameter(v), 500);
  };

  return (
    <div
      style={{
        width: "calc(100% - 20px)", // Changed from fixed width to dynamic width
        maxHeight: "calc(100vh - 180px)",
        overflow: "auto",
        border: "1px solid #ccc",
        borderRadius: 8,
        padding: 16,
        boxSizing: "border-box",
        background: "#fff",
      }}
    >
      <h3 style={{ marginTop: 0 }}>パラメータ設定</h3>

      <div style={{ marginBottom: 12 }}>
        <label htmlFor="threshold">2値化しきい値: {threshold}</label>
      </div>

      <input
        id="threshold"
        type="range"
        min={0}
        max={255}
        value={threshold}
        onChange={handleSliderChange}
        style={{ width: "100%" }}
      />

      <div style={{ marginTop: 12 }}>
        <button onClick={() => onSave(threshold)}>Save</button>
      </div>
    </div>
  );
};

export default ParameterSetter;
