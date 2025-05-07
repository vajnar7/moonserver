import queue
import time
from threading import Thread
from queue import Queue

device_in = Queue()
device_out = Queue()
user_out = Queue()
user_in = Queue()
user_ping = Queue()


def wait_for_command(q):
    try:
        res = q.get(block=True, timeout=1)
    except queue.Empty:
        res = "NOP"

    return res


class StatusStateMachine(Thread):
    def __init__(self):
        super().__init__(target=self.run)
        self._current_state = "IDLE"
        self._running = False

    def start(self):
        self._running = True
        super().start()

    def _process_unsolicied_commands(self):
        val = wait_for_command(device_in)

        if val.startswith("ERROR"):
            user_ping.put(val)
            self._current_state = "ERROR"
        elif val.startswith("WARNING"):
            user_ping.put(val)
        elif val.startswith("INFO"):
            user_ping.put(val)

    def run(self):
        while self._running:
            # teleskop v stanju cakanja na novo komando
            if self._current_state == "IDLE":
                res = wait_for_command(user_out)
                val = res.split(" ")
                if val[0] == "MVST?":
                    device_out.put(res)
                    self._current_state = "WAITING"
                elif val[0] == "MV":
                    device_out.put(res)
                    self._current_state = "WAITING"
                elif val[0] == "BTRY?":
                    device_out.put(res)
                    self._current_state = "WAITING"
                elif val[0] == "MVS":
                    device_out.put(res)
                    self._current_state = "WAITING"

                self._process_unsolicied_commands()
            # teleskop v stanju WAITING
            elif self._current_state == "WAITING":
                val = wait_for_command(device_in)
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
                elif val.startswith("MVS_ACK"):
                    user_in.put(val)
                    self._current_state = "MOVING"
            # teleskop je v stanju MOVING
            elif self._current_state == "MOVING":
                val = wait_for_command(user_out)
                print("iz userja dobil " + val)
                if val == "MVE":
                    device_out.put(val)
                time.sleep(0.5)
                val = wait_for_command(device_in)
                print("iz devicea dobil " + val)
                if val == "MVE_ACK":
                    user_in.put(val)
                    self._current_state = "IDLE"

                self._process_unsolicied_commands()
            # teleskop je v stanju ERROR
            elif self._current_state == "ERROR":
                self._process_unsolicied_commands()

