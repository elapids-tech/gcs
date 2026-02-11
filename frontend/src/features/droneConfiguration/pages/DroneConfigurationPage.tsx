import React, { useEffect, useRef, useState } from "react";
import CameraFrameViewer from "../components/CameraFrameViewer";
import ParameterSetter from "../components/ParameterSetter";

const DroneConfigurationPage: React.FC = () => {
  const hbTimerRef = useRef<number | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [leftWidth, setLeftWidth] = useState<number>(900);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [isSplitterHovered, setIsSplitterHovered] = useState<boolean>(false);

  const minLeft = 480;
  const minRight = 280;
  const splitterWidth = 4;
  const splitterGap = 5;

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

  useEffect(() => {
    const handlePointerMove = (event: PointerEvent) => {
      if (!isDragging || !containerRef.current) return;

      const rect = containerRef.current.getBoundingClientRect();
      const maxLeft = Math.max(minLeft, rect.width - minRight - splitterWidth - splitterGap * 2);
      const nextLeft = Math.min(Math.max(event.clientX - rect.left, minLeft), maxLeft);
      setLeftWidth(nextLeft);
    };

    const handlePointerUp = () => {
      if (isDragging) setIsDragging(false);
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);

    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
    };
  }, [isDragging, minLeft, minRight]);

  return (
    <div style={{ padding: "16px" }}>
      <h2>Drone Configuration</h2>
      <div ref={containerRef} style={{ display: "flex", gap: 0 }}>
        <div style={{ width: leftWidth, minWidth: minLeft, marginRight: splitterGap }}>
          <CameraFrameViewer />
        </div>
        <div
          role="separator"
          aria-orientation="vertical"
          onPointerEnter={() => setIsSplitterHovered(true)}
          onPointerLeave={() => setIsSplitterHovered(false)}
          onPointerDown={(event) => {
            event.preventDefault();
            setIsDragging(true);
            event.currentTarget.setPointerCapture(event.pointerId);
          }}
          style={{
            width: splitterWidth,
            cursor: "col-resize",
            background: isSplitterHovered
              ? "#e5e7eb"
              : "linear-gradient(90deg, transparent 0, transparent 1px, #d1d5db 1px, #d1d5db 2px, transparent 2px)",
          }}
        />
        <div style={{ flex: 1, minWidth: minRight, marginLeft: splitterGap }}>
          <ParameterSetter />
        </div>
      </div>
    </div>
  );
};

export default DroneConfigurationPage;
