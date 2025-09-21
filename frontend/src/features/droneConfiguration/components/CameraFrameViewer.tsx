import React, { useEffect, useMemo, useRef, useState } from "react";

export interface CameraFrameViewerProps {
  wsUrl: string;
  minWidth?: number;
  maxWidth?: number;
  minHeight?: number;
  maxHeight?: number;
  aspectRatio?: number;      // width / height
  resizeDebounceMs?: number; // ドラッグ終了までの待ち時間
}

const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));

const CameraFrameViewer: React.FC<CameraFrameViewerProps> = ({
  wsUrl,
  minWidth = 640,
  maxWidth = 1280,
  minHeight = 400,
  maxHeight = 800,
  aspectRatio = 16 / 10,
  resizeDebounceMs = 250,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const debounceTimerRef = useRef<number | null>(null);

  const [connected, setConnected] = useState(false);
  const [imageUrl, setImageUrl] = useState<string | null>(null);

  // 確定サイズ（ドラッグ中は更新しない）
  const [size, setSize] = useState<{ width: number; height: number }>(() => {
    const w = clamp(960, minWidth, maxWidth);
    const h = clamp(Math.round(960 / aspectRatio), minHeight, maxHeight);
    return { width: w, height: h };
  });

  // Resize event listener
  useEffect(() => {
    const handleResize = () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
      debounceTimerRef.current = window.setTimeout(() => {
        if (containerRef.current) {
          const containerWidth = containerRef.current.offsetWidth;
          console.log("Container width:", containerWidth); // Debug log
          const newWidth = clamp(containerWidth, minWidth, maxWidth);
          const newHeight = clamp(Math.round(newWidth / aspectRatio), minHeight, maxHeight);
          setSize({ width: newWidth, height: newHeight });
        }
      }, resizeDebounceMs);
    };

    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, [minWidth, maxWidth, minHeight, maxHeight, aspectRatio, resizeDebounceMs]);

  // WebSocket
  useEffect(() => {
    const ws = new WebSocket(wsUrl);
    ws.binaryType = "arraybuffer";
    wsRef.current = ws;

    ws.onopen  = () => setConnected(true);
    ws.onerror = () => setConnected(false);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (event) => {
      const blob = new Blob([event.data], { type: "image/jpeg" });
      const url = URL.createObjectURL(blob);
      setImageUrl(url);
    };

    return () => {
      ws.close();
      if (imageUrl) {
        URL.revokeObjectURL(imageUrl);
      }
    };
  }, [wsUrl, imageUrl]);

  const placeholder = useMemo(
    () => (
      <div
        style={{
          width: size.width,
          height: size.height,
          background: "#1f1f1f",
          color: "#ddd",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          border: "1px solid #3a3a3a",
          boxSizing: "border-box",
          textAlign: "center",
        }}
      >
        <div>
          <div style={{ fontSize: 28, letterSpacing: 2, marginBottom: 8 }}>
            NO CONNECTION
          </div>
          <div style={{ fontSize: 14, opacity: 0.8 }}>
            Waiting for UDP frames…
          </div>
        </div>
      </div>
    ),
    [size.width, size.height]
  );

  return (
    <div
      ref={containerRef}
      style={{
        width: "100%",     // 左カラムの幅に追従（右寄せは親の flex が担保）
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {connected && imageUrl ? (
        <img
          src={imageUrl}
          alt="drone-stream"
          width={size.width}
          height={size.height}
          style={{
            display: "block",
            objectFit: "contain",
            border: "1px solid #ccc",
            boxSizing: "border-box",
          }}
        />
      ) : (
        placeholder
      )}
    </div>
  );
};

export default CameraFrameViewer;
