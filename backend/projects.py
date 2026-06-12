import json
import os
import socket
import urllib.error
import urllib.request

from fastapi import APIRouter

projects = APIRouter(prefix="/projects", tags=["projects"])
# Backward compatible alias used by backend.main import.
flight_area = projects
app_settings_json_path = os.path.join(os.path.dirname(__file__), "app_settings.json")


def _read_sfm_server_settings() -> tuple[str, int]:
    try:
        with open(app_settings_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return "", 0

    network = data.get("network", {}) if isinstance(data, dict) else {}
    if not isinstance(network, dict):
        return "", 0

    sfm = network.get("sfm-server", {})
    if not isinstance(sfm, dict):
        return "", 0

    ip = str(sfm.get("ip", "")).strip()
    try:
        port = int(sfm.get("port", 0) or 0)
    except (TypeError, ValueError):
        port = 0

    return ip, port

@projects.get("/sfm-server-info")
def get_sfm_server_info():
    ip, port = _read_sfm_server_settings()
    return {
        "status": "ok",
        "ip": ip,
        "port": port,
    }

@projects.post("/check-connection")
def check_connection(ip: str, port: int):
    ip = ip.strip()
    port = int(port)

    if not ip:
        return {"status": "error", "message": "IP is required."}
    if not (1 <= port <= 65535):
        return {"status": "error", "message": "Port must be between 1 and 65535."}

    host_port = f"{ip}:{port}"
    url = f"http://{host_port}/health"
    try:
        with urllib.request.urlopen(url, timeout=2.0) as resp:
            ok = 200 <= resp.status < 300
            return {
                "status": "ok" if ok else "error",
                "reachable": ok,
                "http_status": resp.status,
            }
    except urllib.error.HTTPError as exc:
        return {
            "status": "error",
            "reachable": False,
            "http_status": exc.code,
            "message": "HTTP error",
        }
    except (urllib.error.URLError, socket.timeout) as exc:
        return {
            "status": "error",
            "reachable": False,
            "message": f"Connection failed: {type(exc).__name__}",
        }

