import json
import os
import socket
import urllib.error
import urllib.request

from fastapi import APIRouter

app_setting = APIRouter(prefix="/app-setting", tags=["app-setting"])

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "app_settings.json")


def _default_settings() -> dict:
	return {
		"network": {
			"sfm-server": {
				"ip": "",
				"port": 0,
			}
		}
	}


def _normalize_settings(data: dict) -> dict:
	settings = data if isinstance(data, dict) else {}
	network = settings.get("network", {})
	if not isinstance(network, dict):
		network = {}

	sfm = network.get("sfm-server", {})
	if not isinstance(sfm, dict):
		sfm = {}

	network["sfm-server"] = {
		"ip": str(sfm.get("ip", "")).strip(),
		"port": int(sfm.get("port", 0) or 0),
	}
	settings["network"] = network
	return settings


def ensure_settings_file() -> None:
	if not os.path.exists(SETTINGS_FILE):
		_save_settings(_default_settings())
		return

	current = _load_settings()
	normalized = _normalize_settings(current)
	if normalized != current:
		_save_settings(normalized)


def _load_settings() -> dict:
	if not os.path.exists(SETTINGS_FILE):
		return {}

	try:
		with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
			data = json.load(f)
		return data if isinstance(data, dict) else {}
	except (OSError, json.JSONDecodeError):
		return {}


def _save_settings(data: dict) -> None:
	with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
		json.dump(data, f, indent=2, ensure_ascii=False)


def _read_network_entry(key: str) -> dict:
	data = _load_settings()
	network = data.get("network", {}) if isinstance(data, dict) else {}
	if not isinstance(network, dict):
		return {}
	entry = network.get(key, {})
	return entry if isinstance(entry, dict) else {}


def _write_network_entry(key: str, ip: str, port: int) -> None:
	data = _load_settings()
	network = data.get("network", {}) if isinstance(data, dict) else {}
	if not isinstance(network, dict):
		network = {}

	network[key] = {
		"ip": ip.strip(),
		"port": int(port),
	}
	data["network"] = network
	_save_settings(data)


def _check_connection(ip: str, port: int):
	ip = ip.strip()
	port = int(port)

	if not ip:
		return {"status": "error", "message": "IP is required."}
	if not (1 <= port <= 65535):
		return {"status": "error", "message": "Port must be between 1 and 65535."}

	host_port = f"{ip}:{port}"
	url = f"http://{host_port}/health"
	try:
		with urllib.request.urlopen(url, timeout=3.0) as resp:
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


@app_setting.get("/network/flight-area-build-server")
def read_flight_area_build_server_network():
    entry = _read_network_entry("flight-area-build-server")
    return {
        "status": "ok",
        "ip": entry.get("ip", ""),
        "port": entry.get("port", 0),
    }

@app_setting.post("/network/flight-area-build-server")
def write_flight_area_build_server_network(ip: str, port: int):
	_write_network_entry("flight-area-build-server", ip, port)
	return {"status": "ok"}


@app_setting.get("/network/sfm-server")
def read_sfm_server_network():
	entry = _read_network_entry("sfm-server")
	if not entry:
		entry = _read_network_entry("flight-area-build-server")

	return {
		"status": "ok",
		"ip": entry.get("ip", ""),
		"port": entry.get("port", 0),
	}


@app_setting.post("/network/sfm-server")
def write_sfm_server_network(ip: str, port: int):
	_write_network_entry("sfm-server", ip, port)
	return {"status": "ok"}


@app_setting.post("/network/sfm-server/check")
def check_sfm_server_connection(ip: str, port: int):
	return _check_connection(ip, port)
