import React, { useEffect, useRef, useState } from "react";

const CameraFrameViewer: React.FC = () => {
  const [topImageUrl, setTopImageUrl] = useState("");
  const [bottomImageUrl, setBottomImageUrl] = useState("");
  const [isDisconnected, setIsDisconnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const lastUrlsRef = useRef<{ top: string | null; bottom: string | null }>({
    top: null,
    bottom: null,
  });

  const toBlobUrl = (base64: string) => {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) {
      bytes[i] = binary.charCodeAt(i);
    }
    const blob = new Blob([bytes], { type: "image/jpeg" });
    return URL.createObjectURL(blob);
  };

  useEffect(() => {
    const WS_URL = "ws://localhost:8003/ws/video";
    const ws = new WebSocket(WS_URL);
    ws.binaryType = "arraybuffer";
    wsRef.current = ws;

    ws.onmessage = (event) => {
      if (typeof event.data === "string") {
        const payload = JSON.parse(event.data);
        const topUrl = toBlobUrl(payload.left);
        const bottomUrl = toBlobUrl(payload.right);

        setTopImageUrl(topUrl);
        setBottomImageUrl(bottomUrl);
        setIsDisconnected(false);

        if (lastUrlsRef.current.top) URL.revokeObjectURL(lastUrlsRef.current.top);
        if (lastUrlsRef.current.bottom) URL.revokeObjectURL(lastUrlsRef.current.bottom);
        lastUrlsRef.current = { top: topUrl, bottom: bottomUrl };
        return;
      }

      const blob = new Blob([event.data], { type: "image/jpeg" });
      const url = URL.createObjectURL(blob);
      setTopImageUrl(url);
      setBottomImageUrl("");
      setIsDisconnected(false);

      if (lastUrlsRef.current.top) URL.revokeObjectURL(lastUrlsRef.current.top);
      if (lastUrlsRef.current.bottom) URL.revokeObjectURL(lastUrlsRef.current.bottom);
      lastUrlsRef.current = { top: url, bottom: null };
    };

    ws.onopen = () => setIsDisconnected(false);

    ws.onclose = () => setIsDisconnected(true);

    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
      setIsDisconnected(true);
    };

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      if (lastUrlsRef.current.top) URL.revokeObjectURL(lastUrlsRef.current.top);
      if (lastUrlsRef.current.bottom) URL.revokeObjectURL(lastUrlsRef.current.bottom);
      lastUrlsRef.current = { top: null, bottom: null };
    };
  }, []);

  return (
    <div>
      <h3>Drone Camera Stream</h3>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>Camera 0</div>
          <div
            style={{
              width: "100%",
              aspectRatio: "800 / 600",
              border: "1px solid #ccc",
              background: "#f3f4f6",
            }}
          >
            {topImageUrl ? (
              <img
                src={topImageUrl}
                alt="drone-stream-camera-0"
                style={{ width: "100%", height: "100%", objectFit: "contain", display: "block" }}
              />
            ) : (
              <svg
                role="img"
                aria-label="drone-stream-camera-0"
                viewBox="0 0 800 600"
                preserveAspectRatio="xMidYMid meet"
                style={{ width: "100%", height: "100%", display: "block" }}
              >
                <rect width="800" height="600" fill="#f3f4f6" />
                <rect x="1" y="1" width="798" height="598" fill="none" stroke="#d1d5db" />
                <text
                  x="50%"
                  y="50%"
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontFamily="Arial, sans-serif"
                  fontSize="36"
                  fill="#374151"
                >
                  {isDisconnected ? "Disconnected from backend" : "Waiting for camera stream"}
                </text>
              </svg>
            )}
          </div>
        </div>

        <div>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>Camera 1</div>
          <div
            style={{
              width: "100%",
              aspectRatio: "800 / 600",
              border: "1px solid #ccc",
              background: "#f3f4f6",
            }}
          >
            {bottomImageUrl ? (
              <img
                src={bottomImageUrl}
                alt="drone-stream-camera-1"
                style={{ width: "100%", height: "100%", objectFit: "contain", display: "block" }}
              />
            ) : (
              <svg
                role="img"
                aria-label="drone-stream-camera-1"
                viewBox="0 0 800 600"
                preserveAspectRatio="xMidYMid meet"
                style={{ width: "100%", height: "100%", display: "block" }}
              >
                <rect width="800" height="600" fill="#f3f4f6" />
                <rect x="1" y="1" width="798" height="598" fill="none" stroke="#d1d5db" />
                <text
                  x="50%"
                  y="50%"
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontFamily="Arial, sans-serif"
                  fontSize="36"
                  fill="#374151"
                >
                  {isDisconnected ? "Disconnected from backend" : "Waiting for camera stream"}
                </text>
              </svg>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default CameraFrameViewer;
