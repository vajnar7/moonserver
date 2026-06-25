import threading
from enum import Enum


class MachineState(Enum):
    READY = "ready"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    MOVING = "moving"
    ERROR = "error"


class IOEmulator:
    def __init__(self, command_queue, response_queue):
        self.state = MachineState.READY
        self.error_data = None
        self.command_queue = command_queue
        self.response_queue = response_queue
        self._lock = threading.Lock()

    def _send_response(self, success, message):
        self.response_queue.put({
            "success": success,
            "message": message,
            "state": self.state.value,
            "error_data": None if success else self.error_data,
        })

    def _simulate_connect(self):
        with self._lock:
            if self.state != MachineState.CONNECTING:
                return
            self.state = MachineState.CONNECTED
            self.error_data = None
            self._send_response(True, "Connection established.")
            print("Emulator: connect succeeded")

    def _simulate_move(self, steps_a, steps_e):
        with self._lock:
            if self.state != MachineState.MOVING:
                return

            self.state = MachineState.CONNECTED
            self.error_data = None
            self._send_response(True, "Move acknowledged.")
            print(f"Emulator: move of {steps_a} units along axis A and {steps_e} units along axis E acknowledged")

    def _handle_connect(self):
        with self._lock:
            print(f"Emulator: current state is {self.state}")
            if self.state not in (MachineState.READY, MachineState.ERROR):
                self.error_data = f"Cannot connect from state {self.state.value}."
                self._send_response(False, self.error_data)
                return
            self.state = MachineState.CONNECTING
            self.error_data = None
            print("Emulator: received connect command, waiting to respond...")

        threading.Timer(1.0, self._simulate_connect).start()

    def _handle_move(self, steps_a, steps_e):
        with self._lock:
            if self.state != MachineState.CONNECTED:
                self.error_data = f"Cannot move from state {self.state.value}."
                self._send_response(False, self.error_data)
                return
            self.state = MachineState.MOVING
            self.error_data = None
            print(f"Emulator: received move command for {steps_a} units along axis A and {steps_e} units along axis E, waiting to respond...")

        threading.Timer(1.5, self._simulate_move, args=(steps_a, steps_e)).start()

    def _handle_command(self, command):
        command_type = command.get("type")
        if command_type == "connect":
            print("Emulator: handling connect command")
            self._handle_connect()
            return
        if command_type == "move":
            self._handle_move(command.get("steps_a", 0), command.get("steps_e", 0))
            return

        print(f"Emulator: unknown command {command_type}")
        self.response_queue.put({
            "success": False,
            "message": f"Unknown command: {command_type}",
            "state": self.state.value,
            "error_data": self.error_data,
        })


    def _run(self):
        print("I/O emulator started and waiting for commands on the queue.")
        while True:
            try:
                command = self.command_queue.get()
            except:
                print("Emulator: no command received, checking again...")
                continue

            if not isinstance(command, dict):
                continue

            print(f"Emulator: processing command {command}")
            self._handle_command(command)

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()


def start_emulator(command_queue, response_queue):
    emulator = IOEmulator(command_queue, response_queue)
    emulator.start()

