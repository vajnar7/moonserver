import threading
from enum import Enum
from flask import Flask, jsonify, request

app = Flask(__name__)

class MachineState(Enum):
    READY = "ready"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"

class StateMachine:
    def __init__(self):
        self.state = MachineState.READY
        self.error_data = None
        self._lock = threading.Lock()
        self._connect_timeout = None

    def _set_state(self, state, error_data=None):
        self.state = state
        self.error_data = error_data

    def _cancel_timeout(self):
        if self._connect_timeout is not None:
            self._connect_timeout.cancel()
            self._connect_timeout = None

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

    def receive_io_response(self, success: bool, message: str | None = None):
        with self._lock:
            if self.state != MachineState.CONNECTING:
                return {
                    "success": False,
                    "message": f"No pending connection to complete from state {self.state.value}.",
                    "state": self.state.value,
                    "error_data": self.error_data,
                }

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

    def status(self):
        with self._lock:
            return {
                "state": self.state.value,
                "error_data": self.error_data,
            }

machine = StateMachine()

@app.route("/command/connect", methods=["POST"])
def command_connect():
    result = machine.connect()
    return jsonify(result)

@app.route("/command/connect/response", methods=["POST"])
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
    app.run(host="0.0.0.0", port=5000, debug=True)
