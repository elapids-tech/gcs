import json
import os

from fastapi import APIRouter

app_setting = APIRouter(prefix="/app-setting", tags=["app-setting"])

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "app_settings.json")


@app_setting.get("/network/flight-area-build-server")
def read_flight_area_build_server_network():
	if not os.path.exists(SETTINGS_FILE):
		return {"status": "error", "message": "Settings not found"}
	with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
		data = json.load(f)
	network = data.get("network", {}) if isinstance(data, dict) else {}
	entry = network.get("flight-area-build-server", {}) if isinstance(network, dict) else {}
	return {
		"status": "ok",
		"ip": entry.get("ip", ""),
		"port": entry.get("port", 0),
	}

@app_setting.post("/network/flight-area-build-server")
def write_flight_area_build_server_network(ip: str, port: int):
	payload = {
		"network": {
			"flight-area-build-server": {
				"ip": ip.strip(),
				"port": int(port),
			}
		}
	}
	with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
		json.dump(payload, f, indent=2, ensure_ascii=False)

	return {"status": "ok"}
