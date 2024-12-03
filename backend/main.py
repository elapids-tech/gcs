import json
import os
import time
import asyncio
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List
from typing import Dict

from drone_controller import DroneController

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

class ProjectManager:
    def __init__(self) -> None:
        self.last_update = time.time()
        self.coordinates = {"x": 0, "y": 0, "z": 0}
        self.landmarks = []

    def update_coordinates(self):
        if self.coordinates['x'] == 10:
            self.coordinates['x'] = 0
            self.coordinates['y'] = 0
            self.coordinates['z'] = 0
        else:
            self.coordinates['x'] += 1
            self.coordinates['y'] += 1
            self.coordinates['z'] += 1

        self.last_update = time.time()

    def add_landmark(self, id, x, y, z):
        self.landmarks.append({"id":id, "x": x, "y": y, "z": z})

    def get_coordinates(self):
        return self.coordinates

drone_controller = DroneController(interval=0.01, host='192.168.0.6', port=5000)
drone_controller.start()

manager = ConnectionManager()
project = ProjectManager()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    print("WebSocket connection established") 
    try:
        while True:
            result = drone_controller.get_drone_attitude_axis()
            if result == None:
                continue

            data = {
                "key": "dronePosUpdate",
                "value": result
            }
            
            print('send json data:', data)
            await websocket.send_text(json.dumps(data))
            await asyncio.sleep(0.05) 

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("WebSocket disconnected") 


@app.post("/upload/")
async def upload_file(request: Request):
    body = await request.body()
    json_data = body.decode('utf-8')

    data = json.loads(json_data)

    project.landmarks.clear()

    for landmark in data:
        id = str(landmark['id'])
        pos = landmark['center']
        project.landmarks.append({"id":id, "x":pos[0], "y":pos[1], "z":pos[2]})

    print(project.landmarks)
    await manager.broadcast(json.dumps(project.landmarks))

    return {"state_message": 0}

@app.post("/start")
def start():
    print('start pressed')
    drone_controller.set_drone_state(1)
    print(f'drone_state:{drone_controller.drone_state}')
    return {"status": f"{drone_controller.drone_state}"}

@app.post("/stop")
def stop():
    print('stop pressed')
    drone_controller.set_drone_state(0)
    print(f'drone_state:{drone_controller.drone_state}')
    return {"status": f"{drone_controller.drone_state}"}


# @app.route("/api/trajectory-planning", methods=["POST"])
# def trajectory_planning_api():
#     data = json.loads(request.data)

#     waypoint_groups = [] # grouped by continuious movement (no stopping)
#     for waypoint in data["waypoints"]:
#         stop_at_waypoint = waypoint[-1]
#         if stop_at_waypoint:
#             waypoint_groups.append([waypoint[:3*num_objects]])
#         else:
#             waypoint_groups[-1].append(waypoint[:3*num_objects])
    
#     setpoints = []
#     for i in range(0, len(waypoint_groups)-1):
#         start_pos = waypoint_groups[i][0]
#         end_pos = waypoint_groups[i+1][0]
#         waypoints = waypoint_groups[i][1:]
#         setpoints += plan_trajectory(start_pos, end_pos, waypoints, data["maxVel"], data["maxAccel"], data["maxJerk"], data["timestep"])

#     return json.dumps({
#         "setpoints": setpoints
#     })

# def plan_trajectory(start_pos, end_pos, waypoints, max_vel, max_accel, max_jerk, timestep):
#     otg = Ruckig(3*num_objects, timestep, len(waypoints))  # DoFs, timestep, number of waypoints
#     inp = InputParameter(3*num_objects)
#     out = OutputParameter(3*num_objects, len(waypoints))

#     inp.current_position = start_pos
#     inp.current_velocity = [0,0,0]*num_objects
#     inp.current_acceleration = [0,0,0]*num_objects

#     inp.target_position = end_pos
#     inp.target_velocity = [0,0,0]*num_objects
#     inp.target_acceleration = [0,0,0]*num_objects

#     inp.intermediate_positions = waypoints

#     inp.max_velocity = max_vel*num_objects
#     inp.max_acceleration = max_accel*num_objects
#     inp.max_jerk = max_jerk*num_objects

#     setpoints = []
#     res = Result.Working
#     while res == Result.Working:
#         res = otg.update(inp, out)
#         setpoints.append(copy.copy(out.new_position))
#         out.pass_to_input(inp)

#     return setpoints


if __name__ == '__main__':
    pass