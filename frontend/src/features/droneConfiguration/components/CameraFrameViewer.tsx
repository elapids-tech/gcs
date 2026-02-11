import React, { useEffect, useRef, useState } from "react";

const CameraFrameViewer: React.FC = () => {
  const [imageUrl, setImageUrl] = useState("");
  const [isDisconnected, setIsDisconnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const lastUrlRef = useRef<string | null>(null);

  useEffect(() => {
    const WS_URL = "ws://localhost:8003/ws/video";
    const ws = new WebSocket(WS_URL);
    ws.binaryType = "arraybuffer";
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const blob = new Blob([event.data], { type: "image/jpeg" });
      const url = URL.createObjectURL(blob);
      setImageUrl(url);
      setIsDisconnected(false);

      if (lastUrlRef.current) URL.revokeObjectURL(lastUrlRef.current);
      lastUrlRef.current = url;
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
      if (lastUrlRef.current) {
        URL.revokeObjectURL(lastUrlRef.current);
        lastUrlRef.current = null;
      }
    };
  }, []);

  return (
    <div>
      <h3>Drone Camera Stream</h3>
      <div
        style={{
          width: "100%",
          aspectRatio: "1600 / 600",
          border: "1px solid #ccc",
          background: "#f3f4f6",
        }}
      >
        {imageUrl ? (
          <img
            src={imageUrl}
            alt="drone-stream"
            style={{ width: "100%", height: "100%", objectFit: "contain", display: "block" }}
          />
        ) : (
          <svg
            role="img"
            aria-label="drone-stream-disconnected"
            viewBox="0 0 1600 600"
            preserveAspectRatio="xMidYMid meet"
            style={{ width: "100%", height: "100%", display: "block" }}
          >
            <rect width="1600" height="600" fill="#f3f4f6" />
            <rect x="1" y="1" width="1598" height="598" fill="none" stroke="#d1d5db" />
            <text
              x="50%"
              y="50%"
              textAnchor="middle"
              dominantBaseline="middle"
              fontFamily="Arial, sans-serif"
              fontSize="40"
              fill="#374151"
            >
              {isDisconnected
                ? "Disconnected from backend"
                : "Waiting for camera stream"}
            </text>
          </svg>
        )}
      </div>
    </div>
  );
};

export default CameraFrameViewer;
