from telescope.position import Position
from telescope.status_state_machine import StatusStateMachine

ST_READY = 1
ST_NOT_CALIBRATED = 9


class Telescope(Position):
    def __init__(self):
        super().__init__(0, 0)
        self.cur_object = ""
        self.status = ST_NOT_CALIBRATED
        self.state_machine = StatusStateMachine()
        self.state_machine.start()

    @staticmethod
    def _parse_hour_angle(val: str) -> float:
        # 2h31m48.704s
        tmp = val.split("h")
        res = float(tmp[0])
        tmp = tmp[1].split("m")
        res += float(tmp[0]) / 60
        tmp = tmp[1].split("s")
        res += float(tmp[0]) / 3600
        return res

    @staticmethod
    def _parse_angle(val: str) -> float:
        # +89°15'50.72
        tmp = val.split("°")
        res = float(tmp[0])
        tmp = tmp[1].split("'")
        res += float(tmp[0]) / 60 + float(tmp[1]) / 3600
        return res

    def set_cur_obj(self, val: str):
        res = val.split(" ")
        self.cur_object = res[0]
        self.calc_alt_az(self._parse_hour_angle(res[1]), self._parse_angle(res[2]))
