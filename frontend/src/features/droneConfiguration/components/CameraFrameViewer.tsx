import React, { useEffect, useRef, useState } from "react";

const CameraFrameViewer: React.FC = () => {
  const [imageUrl, setImageUrl] = useState("");
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

      if (lastUrlRef.current) URL.revokeObjectURL(lastUrlRef.current);
      lastUrlRef.current = url;
    };

    ws.onerror = (err) => console.error("WebSocket error:", err);

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
      <h3>ドローン映像</h3>
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

export default CameraFrameViewer;
