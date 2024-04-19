import queue
from threading import Thread

from controller.io import write_to_device, read_from_device
from telescope.status_state_machine import device_in, device_out


class DeviceIOMachine(Thread):
    def __init__(self):
        super().__init__(target=self.run)
        self._current_state = "IDLE"
        self._running = False

    def start(self):
        self._running = True
        super().start()

    def run(self):
        while self._running:
            res = read_from_device()
            device_in.put(res)

            try:
                res = device_out.get(block=True, timeout=1)
            except queue.Empty:
                res = "NOP"
            if res != "NOP":
                write_to_device(res)