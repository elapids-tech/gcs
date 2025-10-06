import React, { useEffect, useRef } from "react";
import CameraFrameViewer from "../components/CameraFrameViewer";
import ParameterSetter from "../components/ParameterSetter";

const DroneConfigurationPage: React.FC = () => {
  const hbTimerRef = useRef<number | null>(null);

  useEffect(() => {
    const BACKEND_HTTP = "http://localhost:8003";
    const KEEP_ALIVE_ENDPOINT = `${BACKEND_HTTP}/config-mode/keep-alive`;

    // 初回送信
    fetch(KEEP_ALIVE_ENDPOINT, { method: "POST" }).catch((e) =>
      console.warn("keep-alive 初回送信失敗:", e)
    );

    // 500msごとに送信
    hbTimerRef.current = window.setInterval(() => {
      fetch(KEEP_ALIVE_ENDPOINT, { method: "POST" }).catch((e) =>
        console.warn("keep-alive 送信失敗:", e)
      );
    }, 500);

    return () => {
      if (hbTimerRef.current) {
        clearInterval(hbTimerRef.current);
        hbTimerRef.current = null;
      }
    };
  }, []);

  return (
    <div style={{ padding: "16px" }}>
      <h2>DroneConfigurationPage</h2>
      <div style={{ display: "flex", gap: "24px" }}>
        <div style={{ flex: 1 }}>
          <CameraFrameViewer />
        </div>
        <div style={{ width: "320px" }}>
          <ParameterSetter />
        </div>
      </div>
    </div>
  );
};

export default DroneConfigurationPage;
