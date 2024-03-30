# https://github.com/pyusb/pyusb?tab=readme-ov-file
# https://forum.arduino.cc/t/how-to-read-data-from-any-of-the-usb-ports-using-the-arduino/228207/5

class Connection(object):

    def write(self, message: str):
        raise NotImplementedError
    