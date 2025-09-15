import React, { useEffect, useRef, useState } from "react";

const DroneConfigurationPage: React.FC = () => {
  const [imageUrl, setImageUrl] = useState("");
  const wsRef = useRef<WebSocket | null>(null);
  const hbTimerRef = useRef<number | null>(null);
  const lastUrlRef = useRef<string | null>(null);

  useEffect(() => {
    // === WebSocketで映像を受信 ===
    const WS_URL = "ws://localhost:8003/ws/video"; // backendに合わせて調整
    const ws = new WebSocket(WS_URL);
    ws.binaryType = "arraybuffer";
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const blob = new Blob([event.data], { type: "image/jpeg" });
      const url = URL.createObjectURL(blob);
      setImageUrl(url);

      // 古いURLを解放（メモリリーク防止）
      if (lastUrlRef.current) URL.revokeObjectURL(lastUrlRef.current);
      lastUrlRef.current = url;
    };

    ws.onerror = (err) => console.error("WebSocket error:", err);

    // === 定期的に keep-alive を呼ぶ ===
    const BACKEND_HTTP = "http://localhost:8003";
    const KEEP_ALIVE_ENDPOINT = `${BACKEND_HTTP}/config-mode/keep-alive`;

    // すぐに1回送信
    fetch(KEEP_ALIVE_ENDPOINT, { method: "POST" }).catch((e) =>
      console.warn("keep-alive 初回送信失敗:", e)
    );

    // 500msごとに送信（2Hz）
    hbTimerRef.current = window.setInterval(() => {
      fetch(KEEP_ALIVE_ENDPOINT, { method: "POST" }).catch((e) =>
        console.warn("keep-alive 送信失敗:", e)
      );
    }, 500);

    // === クリーンアップ ===
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      if (hbTimerRef.current) {
        clearInterval(hbTimerRef.current);
        hbTimerRef.current = null;
      }
      if (lastUrlRef.current) {
        URL.revokeObjectURL(lastUrlRef.current);
        lastUrlRef.current = null;
      }
    };
  }, []);

  return (
    <div>
      <h2>ドローン映像</h2>
      {imageUrl && (
        <img
          src={imageUrl}
          alt="drone-stream"
          style={{ width: "100%", maxWidth: "640px", border: "1px solid #ccc" }}
        />
      )}
    </div>
  );
};

export default DroneConfigurationPage;
