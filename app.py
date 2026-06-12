import threading
import time
import queue
from enum import Enum
from queue import Empty
from flask import Flask, jsonify, request
from io_emulator import start_emulator

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
                    "error_data": self.error_data,
                }

            self._cancel_timeout()
            self._set_state(MachineState.CONNECTING)
            self.error_data = None

            print("I/O action: attempting to connect...")

            self._connect_timeout = threading.Timer(3.0, self._connect_timeout_handler)
            self._connect_timeout.daemon = True
            self._connect_timeout.start()

            return {
                "success": True,
                "message": "Connection attempt started.",
                "state": self.state.value,
                "error_data": None,
            }

    def move(self, distance: int):
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

            print(f"I/O action: moving {distance} units...")

            self._move_timeout = threading.Timer(3.0, self._move_timeout_handler)
            self._move_timeout.daemon = True
            self._move_timeout.start()

            return {
                "success": True,
                "message": "Move command started.",
                "state": self.state.value,
                "error_data": None,
            }

    def receive_io_response(self, success: bool, message: str | None = None):
        with self._lock:
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


# def connect_queue_manager(retries: int = 3, delay: float = 1.0) -> bool:
#     global command_queue, response_queue
#     for attempt in range(1, retries + 1):
#         try:
#             command_queue, response_queue = queue_manager.connect_to_manager()
#             print("Connected to the I/O emulator queue manager.")
#             return True
#         except Exception as exc:
#             print(f"Queue manager connect attempt {attempt} failed: {exc}")
#             time.sleep(delay)
#     return False


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
        result = machine.receive_io_response(success=success, message=message)
        print(f"Received emulator response: {response} -> {result}")


def start_response_thread() -> None:
    response_thread = threading.Thread(target=response_listener, daemon=True)
    response_thread.start()


@app.route("/command/connect", methods=["POST"])
def command_connect():
    result = machine.connect()
    if result["success"]:
        command_queue.put({"type": "connect"})
    return jsonify(result)

@app.route("/command/move", methods=["POST"])
def command_move():
    data = request.get_json(silent=True) or {}
    distance = data.get("distance")
    if not isinstance(distance, int):
        return jsonify({
            "success": False,
            "message": "Invalid move request: distance must be an integer.",
            "state": machine.state.value,
            "error_data": machine.error_data,
        })

    result = machine.move(distance)
    if result["success"]:
        command_queue.put({"type": "move", "distance": distance})
    return jsonify(result)

@app.route("/command/response", methods=["POST"])
def command_connect_response():
    data = request.get_json(silent=True) or {}
    success = data.get("success", False)
    message = data.get("message")
    result = machine.receive_io_response(success=success, message=message)
    return jsonify(result)

@app.route("/state", methods=["GET"])
def get_state():
    return jsonify(machine.status())

@app.route("/command/reset", methods=["POST"])
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
