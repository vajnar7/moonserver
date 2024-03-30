import queue
from threading import Thread
from queue import Queue

device_in = Queue()
device_out = Queue()
user_out = Queue()
user_in = Queue()
user_ping = Queue()


class StatusStateMachine(Thread):
    def __init__(self):
        super().__init__(target=self.run)
        self._current_state = "IDLE"
        self._running = False

    def start(self):
        self._running = True
        super().start()

    def _process_unsolicied_commands(self, val):
        if val.startswith("ERROR"):
            user_ping.put(val)
            self._current_state = "ERROR"
        elif val.startswith("WARNING"):
            user_ping.put(val)
            self._current_state = "IDLE"
        elif val.startswith("INFO"):
            user_ping.put(val)
            self._current_state = "IDLE"

    def run(self):
        while self._running:
            # teleskop v stanju cakanja na novo komando
            if self._current_state == "IDLE":
                try:
                    val = user_out.get(block=True, timeout=1)
                except queue.Empty:
                    val = ""
                if val == "MVST?":
                    device_out.put(val)
                    self._current_state = "WAITING"
                elif val.startswith("MV"):
                    device_out.put(val)
                    self._current_state = "WAITING"
                elif val == "BTRY?":
                    device_out.put(val)
                    self._current_state = "WAITING"

                try:
                    val = device_in.get(block=True, timeout=1)
                except queue.Empty:
                    val = ""
                self._process_unsolicied_commands(val)
            # teleskop v stanju WAITING
            elif self._current_state == "WAITING":
                val = device_in.get()
                if val == "MV_ACK":
                    user_in.put(val)
                    self._current_state = "MOVING"
                elif val == "NOT_RDY":
                    user_in.put(val)
                    self._current_state = "IDLE"
                elif val == "RDY":
                    user_in.put(val)
                    self._current_state = "IDLE"
                elif val.startswith("BTRY"):
                    user_in.put(val)
                    self._current_state = "IDLE"
            # teleskop je v stanju MOVING
            elif self._current_state == "MOVING":
                val = device_in.get()
                self._process_unsolicied_commands(val)
                if val == "RDY":
                    user_in.put(val)
                    self._current_state = "IDLE"
            # teleskop je v stanju ERROR
            elif self._current_state == "ERROR":
                val = device_in.get()
                self._process_unsolicied_commands(val)

