import socket
import urllib.error
import urllib.request

from fastapi import APIRouter

flight_area = APIRouter(prefix="/flight-area", tags=["flight-area"])


@flight_area.get("/health")
def health_check():
    return {"status": "ok"}


@flight_area.post("/check-connection")
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
