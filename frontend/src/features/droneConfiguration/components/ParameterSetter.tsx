import React, { useEffect, useState } from "react";

const ParameterSetter: React.FC = () => {
  const [threshold, setThreshold] = useState<number>(128);
  const [isRecording, setIsRecording] = useState<boolean>(false);

  // ページ読み込み時に現在のしきい値を取得
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

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = Number(e.target.value);
    setThreshold(value);

    // URL クエリに値を埋め込んで送信
    fetch(`http://localhost:8003/config-mode/set-bin-threshold?threshold=${value}`, {
      method: "POST",
    }).catch((e) => console.warn("threshold送信失敗:", e));
  };

  const toggleRecording = () => {
    const endpoint = isRecording
      ? "http://localhost:8003/config-mode/stop-recording"
      : "http://localhost:8003/config-mode/start-recording";

    fetch(endpoint, { method: "POST" })
      .then((res) => {
        if (!res.ok) throw new Error("Failed to toggle recording");
        setIsRecording(!isRecording);
      })
      .catch((e) => console.warn("録画トグル失敗:", e));
  };

  return (
    <div>
      <h3>パラメータ設定</h3>
      <label>
        2値化しきい値: {threshold === -1 ? "無効" : threshold}
        <input
          type="range"
          min="-1"
          max="255"
          step="1"
          value={threshold}
          onChange={handleChange}
          style={{ width: "100%" }}
        />
      </label>
    </div>
  );
};

export default ParameterSetter;
