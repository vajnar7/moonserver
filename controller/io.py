import queue
import usb
from queue import Queue
import time

END_LIMIT_SW_TRIG = "END_LIMIT_SW_TRIG"
BTRY_LOW = "BTRY_LOW"
device = Queue()


def write_to_device(cmd: str):
    # telescope
    # telescope.write()cmd
    if cmd != "NOP":
        print("V TELESKOP POSILJAM:", cmd)
        # za test koj vrnem iz naprave
        test_read_device(cmd)
        #


#######################Testiranje##########################
def test_read_device(cur_cmd):
    time.sleep(1)
    if cur_cmd == "MVST?":
        device.put("RDY")
    elif cur_cmd.startswith("MVS"):
        # 1. case not ready, Drive unit is still executing the previous movement
        # ce je teleskop zaposlen se prizge rdeca lucka na klientu
        # device_in.put("NOT_RDY")

        # 2. case zacetek premikanja, Start movement with the specified parameters
        device.put("MVS_ACK")
    elif cur_cmd.startswith("MVE"):
        device.put("MVE_ACK")


def read_from_device() -> str:
    try:
        res = device.get(block=True, timeout=1)
    except queue.Empty:
        res = "NOP"

    return res


def get_all():
    # for dev in usb.core.find(find_all=True):
    #     print(dev)
    dev = usb.core.find(idVendor=0x3151, idProduct=0x2901)
