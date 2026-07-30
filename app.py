import threading
import queue
from enum import Enum
from turtle import speed
from flask import Flask, jsonify, request
import secrets
import datetime
from functools import wraps
from io_emulator import start_emulator, CommandType
from telescope import convert_radec_to_az_el, degrees_to_dms, degrees_to_hms

app = Flask(__name__)

# koliko korakov je potrebno za premik za 1 stopinjo
K_E = 100
K_A = 100

sky_objects = {
    "Polaris": {"ra": 37.95456067, "dec": 89.26410897},
    "Sirius": {"ra": 101.28715533, "dec": -16.71611586},
    "Betelgeuse": {"ra": 88.792939, "dec": 7.407064},
}

class MachineState(Enum):
    READY = "ready"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    MOVING = "moving"
    ERROR = "error"

class StateMachine:
    def __init__(self):
        self.message = "NOT_RDY"
        self.state = MachineState.READY
        self.error_data = None
        self._lock = threading.Lock()
        self._connect_timeout = None
        self._move_timeout = None
        self.is_calibrated = False
        self.cur_object = None
        self.alt = 0.0
        self.az = 0.0
        self.to_obj = None

    def _set_state(self, state, error_data=None):
        self.state = state
        self.error_data = error_data

    def _cancel_timeout(self):
        if self._connect_timeout is not None:
            self._connect_timeout.cancel()
            self._connect_timeout = None
        if self._move_timeout is not None:
            self._move_timeout.cancel()
            self._move_timeout = None

    def _connect_timeout_handler(self):
        with self._lock:
            if self.state != MachineState.CONNECTING:
                return
            print("I/O timeout: no response from I/O, switching to error state")
            self._set_state(
                MachineState.ERROR,
                "Connection failed: no response from I/O",
            )
            self._connect_timeout = None

    def _move_timeout_handler(self):
        with self._lock:
            if self.state != MachineState.MOVING:
                return
            print("I/O timeout: no movement acknowledgement, switching to error state")
            self._set_state(
                MachineState.ERROR,
                "Move failed: no acknowledgement from I/O",
            )
            self._move_timeout = None

    def _send_response(self, success, message: str, data=None):
        self.message = message
        self.error_data = data
        return {
                    "success": success,
                    "message": self.message,
                    "state": self.state.value,
                    "error_data": self.error_data,
        }

    def to_ready(self):
        with self._lock:
            self._cancel_timeout()
            self._set_state(MachineState.READY)

    def connect(self):
        with self._lock:         
            self._cancel_timeout()
            self._set_state(MachineState.CONNECTING)

            print("I/O action: attempting to connect...")

            # self._connect_timeout = threading.Timer(3.0, self._connect_timeout_handler)
            # self._connect_timeout.daemon = True
            # self._connect_timeout.start()

            return self._send_response(True, "SENT", "Sent MV_ST? command to I/O.")

    def move_start(self, direction: str, speed: int):
        with self._lock:
            self._cancel_timeout()
            self._set_state(MachineState.MOVING)

            print(f"I/O action: starting move in direction '{direction}' with speed {speed}...")

            return self._send_response(True, "SENT", f"Sent MVS command to I/O for direction '{direction}' at speed {speed}.")

    def position(self):
        with self._lock:
            self._cancel_timeout()
            return self._send_response(True, f"POSITION {self.alt} {self.az}")

    def calibrated(self):
        with self._lock:
            self._cancel_timeout()
            self.is_calibrated = True
            self.cur_object = "Polaris"
            self.az, self.alt = convert_radec_to_az_el(
                sky_objects[self.cur_object]["ra"], sky_objects[self.cur_object]["dec"],
                latitude_deg=46.48546944,  # Example latitude
                longitude_deg=13.8475167,  # Example longitude
                utc_time=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=2)))
            )
            print(f"I/O action: calibration complete.")

            return self._send_response(True, "CALIBRATED", "Calibration complete.")

    def move_end(self):
        with self._lock:
            self._cancel_timeout()
            self._set_state(MachineState.MOVING)

            print(f"I/O action: stopping previous move...")

            return self._send_response(True, "SENT", f"Sent MVE command to I/O")

    def move(self, steps_e: int, steps_a: int):
        with self._lock:
            self._cancel_timeout()
            self._set_state(MachineState.MOVING)

            print(f"I/O action: moving {steps_a} units along axis A and {steps_e} units along axis E...")
        
            return self._send_response(True, "SENT", "Sent MV command to I/O.")
            
    def get_io_response(self):
        with self._lock:
            return {
                "success": True,
                "message": self.message,
                "state": self.state.value,
                "error_data": self.error_data,
            }

    def receive_io_response(self, success: bool, message: str):
        with self._lock:
            if self.state == MachineState.CONNECTING: # MV_ST?
                self._cancel_timeout()
                if message == "READY":
                    self._set_state(MachineState.CONNECTED)
                    return self._send_response(True, "READY", "Connection established")
                elif message == "NOT_RDY":
                    self._set_state(MachineState.READY)
                    return self._send_response(True, "NOT_RDY", "Connection failed: I/O reported not ready")

                
            if self.state == MachineState.MOVING:
                print("...........................Received I/O response:", message)

                self._cancel_timeout()
                if message == "MVS_ACK":
                    self._set_state(MachineState.MOVING)
                    return self._send_response(True, "MVS_ACK", "Start moving")
                elif message == "MVE_ACK":
                    self._set_state(MachineState.CONNECTED)
                    return self._send_response(True, "MVE_ACK", "Move ended")
                elif message == "NOT_RDY":
                    self._set_state(MachineState.READY)
                    return self._send_response(False, "NOT_RDY", "Move failed: I/O reported not ready")
                elif message == "MV_ACK":
                    self._set_state(MachineState.MOVING)
                    return self._send_response(True, "MV_ACK", "Move acknowledged")
                elif message == "READY":
                    # target reached, update current position
                    self.az, self.alt = convert_radec_to_az_el(
                            sky_objects[self.to_obj]["ra"], sky_objects[self.to_obj]["dec"],
                            latitude_deg=46.48546944,  # Example latitude
                            longitude_deg=13.8475167,  # Example longitude
                            utc_time=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=2)))
                        )
                    self._set_state(MachineState.CONNECTED)
                    return self._send_response(True, "READY", "Move completed and I/O is ready")

            return {
                "success": False,
                "message": f"No pending operation to complete from state {self.state.value}.",
                "state": self.state.value,
                "error_data": self.error_data,
            }

    def status(self):
        with self._lock:
            return {
                "state": self.state.value,
                "error_data": self.error_data,
            }

machine = StateMachine()
command_queue = queue.Queue()
response_queue = queue.Queue()

# --- Simple in-memory token auth (static credentials) ---
# Static username/password for now (placeholder for real user store)
STATIC_USERNAME = "android"
STATIC_PASSWORD = "password123"

# token -> {"username": str, "expires": datetime}
TOKENS: dict[str, dict] = {}
TOKEN_TTL_SECONDS = 60 * 60  # 1 hour

def _generate_token(username: str) -> str:
    token = secrets.token_urlsafe(32)
    expires = datetime.datetime.utcnow() + datetime.timedelta(seconds=TOKEN_TTL_SECONDS)
    TOKENS[token] = {"username": username, "expires": expires}
    return token

def _validate_token(token: str) -> bool:
    if not token:
        return False
    info = TOKENS.get(token)
    if not info:
        return False
    if info["expires"] < datetime.datetime.utcnow():
        # expired
        del TOKENS[token]
        return False
    return True

def auth_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = None
        if auth_header.startswith("Bearer "):
            token = auth_header.split(None, 1)[1].strip()
        if not token:
            token = request.headers.get("X-Auth-Token")

        if not _validate_token(token):
            return jsonify({"success": False, "message": "Unauthorized: invalid or missing token"}), 401
        return func(*args, **kwargs)

    return wrapper

def response_listener() -> None:
    print("Response listener thread started, waiting for responses from the emulator...")
    while True:
        try:
            response = response_queue.get()
        except:
            print(f"Response queue empty")
            continue

        if not isinstance(response, dict):
            continue

        success = response.get("success", False)
        message = response.get("message")

        # ta samo vpise v lokalne spremenljivke masine
        machine.receive_io_response(success=success, message=message)

def start_response_thread() -> None:
    response_thread = threading.Thread(target=response_listener, daemon=True)
    response_thread.start()

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")
    if username == STATIC_USERNAME and password == STATIC_PASSWORD:
        token = _generate_token(username)
        return jsonify({"success": True, "token": token, "expires_in": TOKEN_TTL_SECONDS})

    return jsonify({"success": False, "message": "Invalid credentials"}), 401

@app.route("/command/connect", methods=["POST"])
@auth_required
def command_connect():
    result = machine.connect()
    command_queue.put({"type": CommandType.MVST.value})
    return jsonify(result)

@app.route("/command/movestart", methods=["POST"])
def command_movestart():
    data = request.get_json(silent=True) or {}
    direction = data.get("p1")
    speed = data.get("p2")

    result = machine.move_start(direction, speed)

    if result["success"]:
        command_queue.put({"type": CommandType.MVS.value, "direction": direction, "speed": speed})
    return jsonify(result)

@app.route("/command/moveend", methods=["POST"])
def command_moveend():
    result = machine.move_end()

    if result["success"]:
        command_queue.put({"type": CommandType.MVE.value})
    return jsonify(result)

@app.route("/command/move", methods=["POST"])
def command_move():
    data = request.get_json(silent=True) or {}
    machine.to_obj = data.get("p1")
    to_az, to_alt = convert_radec_to_az_el(
        sky_objects[machine.to_obj]["ra"], sky_objects[machine.to_obj]["dec"],
        latitude_deg=46.48546944,  # Example latitude
        longitude_deg=13.8475167,  # Example longitude
        utc_time=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=2)))
    )

    print(f"Received move command with object: {machine.to_obj}, target elevation: {to_alt}, target azimuth: {to_az}")
    
    steps_e = (to_alt - machine.alt) * K_E
    steps_a = (to_az - machine.az) * K_A
    result = machine.move(steps_e, steps_a)
    if result["success"]:
        command_queue.put({"type": CommandType.MV.value, "steps_a": steps_a, "steps_e": steps_e})
    return jsonify(result)

@app.route("/command/response", methods=["POST"])
def command_connect_response():
    data = request.get_json(silent=True) or {}
    success = data.get("success", True)
    message = data.get("message")
    print(f"R........................{success}")
    result = machine.receive_io_response(success=success, message=message)
    return jsonify(result)

@app.route("/command/ping", methods=["POST"])
def command_ping():
    result = machine.get_io_response()
    return jsonify(result)

@app.route("/state", methods=["GET"])
def get_state():
    return jsonify(machine.status())

@app.route("/command/calibrated", methods=["POST"])
def set_calibrated():
    result = machine.calibrated()
    return jsonify(result)

@app.route("/command/position", methods=["POST"])
def get_position():
    result = machine.position()
    return jsonify(result)

@app.route("/command/reset", methods=["POST"])
@auth_required
def command_reset():
    machine.to_ready()
    return jsonify({
        "success": True,
        "message": "Machine reset to ready state.",
        "state": machine.state.value,
    })

@app.route("/command/getastrodata", methods=["POST"])
def getastrodata():
    def format_coord(ra_deg: float, dec_deg: float):
        ra_hms = degrees_to_hms(ra_deg)
        dec_dms = degrees_to_dms(dec_deg)
        return {
            "ra": {
                "hours": ra_hms[0],
                "minutes": ra_hms[1],
                "seconds": round(ra_hms[2], 3),
            },
            "dec": {
                "degrees": dec_dms[0],
                "minutes": dec_dms[1],
                "seconds": round(dec_dms[2], 3),
            },
        }

    return {
        "data": {
            "Polaris": format_coord(37.95456067, 89.26410897),
            "Sirius": format_coord(101.28715533, -16.71611586),
            "Betelgeuse": format_coord(88.792939, 7.407064),
        }
    }


if __name__ == "__main__":
    # Start the I/O emulator in a separate thread before starting the Flask app
    start_emulator(command_queue, response_queue)
    start_response_thread()
    app.run(host="0.0.0.0", port=5000, debug=True)
