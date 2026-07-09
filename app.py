import threading
import time
import queue
from enum import Enum
from queue import Empty
from flask import Flask, jsonify, request
import secrets
import datetime
from functools import wraps
from io_emulator import start_emulator, CommandType, MessageType

app = Flask(__name__)

class MachineState(Enum):
    READY = "ready"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    MOVING = "moving"
    ERROR = "error"

class StateMachine:
    def __init__(self):
        self.state = MachineState.READY
        self.error_data = None
        self._lock = threading.Lock()
        self._connect_timeout = None
        self._move_timeout = None

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

    def to_ready(self):
        with self._lock:
            self._cancel_timeout()
            self._set_state(MachineState.READY)

    def connect(self):
        with self._lock:
            if self.state not in (MachineState.READY, MachineState.ERROR):
                return {
                    "success": False,
                    "message": f"Cannot connect from state {self.state.value}.",
                    "state": self.state.value,
                    "data": self.error_data,
                }

            self._cancel_timeout()
            self._set_state(MachineState.CONNECTING)

            print("I/O action: attempting to connect...")

            self._connect_timeout = threading.Timer(3.0, self._connect_timeout_handler)
            self._connect_timeout.daemon = True
            self._connect_timeout.start()

            return {
                "success": True,
                "message": "Connection attempt started.",
                "state": self.state.value,
                "data": None,
            }

    def move_start(self, direction: str, speed: int):
        pass  # Placeholder for future implementation of move_start command

    def move(self, steps_a: int, steps_e: int):
        with self._lock:
            if self.state != MachineState.CONNECTED:
                return {
                    "success": False,
                    "message": f"Cannot move from state {self.state.value}.",
                    "state": self.state.value,
                    "error_data": self.error_data,
                }

            self._cancel_timeout()
            self._set_state(MachineState.MOVING)
            self.error_data = None

            print(f"I/O action: moving {steps_a} units along axis A and {steps_e} units along axis E...")
        
            self._move_timeout = threading.Timer(10.0, self._move_timeout_handler)
            self._move_timeout.daemon = True
            self._move_timeout.start()

            return {
                "success": True,
                "message": "Move command started.",
                "state": self.state.value,
                "error_data": None,
            }

    # success = True, stanje je error
    def receive_io_response(self, success: bool, message: str | None = None):
        with self._lock:
            print(f"To pa je trenutno stanje {self.state}")
            if self.state == MachineState.CONNECTING:
                self._cancel_timeout()
                if success:
                    self._set_state(MachineState.CONNECTED)
                    return {
                        "success": True,
                        "message": "Connection established.",
                        "state": self.state.value,
                        "error_data": None,
                    }
                print(f"Vajnar ta ga pofetin I")
                self._set_state(
                    MachineState.ERROR,
                    message or "Connection failed: I/O reported failure",
                )
                return {
                    "success": False,
                    "message": self.error_data,
                    "state": self.state.value,
                    "error_data": self.error_data,
                }

            if self.state == MachineState.MOVING:
                self._cancel_timeout()
                if success:
                    self._set_state(MachineState.CONNECTED)
                    return {
                        "success": True,
                        "message": "Move acknowledged.",
                        "state": self.state.value,
                        "error_data": None,
                    }
                print(f"Vajnar ta ga pofetin II {success}")
                self._set_state(
                    MachineState.ERROR,
                    message or "Move failed: I/O reported failure",
                )
                return {
                    "success": False,
                    "message": self.error_data,
                    "state": self.state.value,
                    "error_data": self.error_data,
                }

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
        print(f"L.......................{success}")
        result = machine.receive_io_response(success=success, message=message)
        # print(f"Received emulator response: {response} -> {result}")
        print(f"To pride iz emulatorja: {success} | {message} ")
        print(f"To pa je stanje po tem: {result['state']} | {result['error_data']}")

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
    if result["success"]:
        command_queue.put({"type": "connect"})
    return jsonify(result)

@app.route("/command/movestart", methods=["POST"])
def command_move():
    data = request.get_json(silent=True) or {}
    direction = data.get("p1")
    speed = data.get("p2")

    result = machine.move_start(direction, speed)
    if result["success"]:
        command_queue.put({"type": CommandType.MVST, "direction": direction, "speed": speed})
    return jsonify(result)

@app.route("/command/move", methods=["POST"])
def command_move():
    steps_a = 0
    steps_e = 0

    data = request.get_json(silent=True) or {}
    distance = data.get("p1")
    object = data.get("p2")
    if object:
        # skalkuliraj koliko korakov se mora premakniti
        print(f"Received move command with object: {object}")
    else:
        if distance == "left":
            steps_a = -10
        elif distance == "right":
            steps_a = 10
        elif distance == "up":  
            steps_e = 10
        elif distance == "down":
            steps_e = -10

    result = machine.move(steps_a, steps_e)
    if result["success"]:
        command_queue.put({"type": "move", "steps_a": steps_a, "steps_e": steps_e})
    return jsonify(result)

@app.route("/command/response", methods=["POST"])
def command_connect_response():
    data = request.get_json(silent=True) or {}
    success = data.get("success", True)
    message = data.get("message")
    print(f"R........................{success}")
    result = machine.receive_io_response(success=success, message=message)
    return jsonify(result)

@app.route("/state", methods=["GET"])
def get_state():
    return jsonify(machine.status())

@app.route("/command/reset", methods=["POST"])
@auth_required
def command_reset():
    machine.to_ready()
    return jsonify({
        "success": True,
        "message": "Machine reset to ready state.",
        "state": machine.state.value,
    })

if __name__ == "__main__":
    # Start the I/O emulator in a separate thread before starting the Flask app
    start_emulator(command_queue, response_queue)
    start_response_thread()
    app.run(host="0.0.0.0", port=5000, debug=True)
