import math
from datetime import datetime

# https://www.rs-online.com/designspark/types-of-displacement-sensor-working-principle-and-characteristic
# http://www.stargazing.net/kepler/altaz.html

DEF_LONGITUDE = 13.82
DEF_LATITUDE = 46.45
MOTOR_STEPS_NUM = 200.0
REDUCTOR_TRANSLATION = 30.0
BELT_TRANSLATION = 48.0 / 14.0
K = MOTOR_STEPS_NUM * REDUCTOR_TRANSLATION * BELT_TRANSLATION


class Position(object):
    ra, dec, az, alt = 0, 0, 0, 0
    cur_h_steps, cur_v_steps = 0, 0
    dif_h_steps, dif_v_steps = 0, 0

    longitude = DEF_LONGITUDE
    latitude = DEF_LATITUDE

    def __init__(self, ra, dec):
        self.ra = ra
        self.dec = dec
        self._ra_dec_2_alt_az()

    def calc_alt_az(self, ra, dec):
        self.ra = ra
        self.dec = dec
        self._ra_dec_2_alt_az()

    def calc_ra_dec(self, alt, az):
        self.alt = alt
        self.az = az
        self._alt_az_2_ra_dec()

    def calc_steps(self, new_ra, new_dec):
        prev_ra, prev_dec = self.ra, self.dec
        prev_alt, prev_az = self.alt, self.az
        self.calc_alt_az(new_ra, new_dec)
        dif_alt = self.alt - prev_alt
        dif_az = self.az - prev_az
        self.dif_h_steps = (dif_az * K) / 360.0
        self.dif_v_steps = (dif_alt * K) / 360.0

    @staticmethod
    def _get_utc():
        utc = datetime.utcnow()
        return utc.hour + utc.minute / 60 + utc.second / 3600

    def _get_siderial_time(self):
        diff = datetime.utcnow() - datetime(2000, 1, 1)
        j2000 = diff.total_seconds() / 86400
        lst = 100.46 + 0.985647 * j2000 + self.longitude + 15 * self._get_utc()
        return lst % 360

    def _alt_az_2_ra_dec(self):
        alt = math.radians(self.alt)
        az = math.radians(self.az)
        lon = math.radians(self.longitude)

        sin_d = math.sin(alt) * math.sin(lon) + math.cos(alt) * math.cos(lon) * math.cos(az)
        d = math.asin(sin_d)
        cos_h = (math.sin(alt) - math.sin(lon) * math.sin(d)) / (math.cos(lon) * math.cos(d))

        ra = self._get_siderial_time() - math.acos(cos_h)
        self.dec = math.degrees(d)
        self.ra = math.degrees(ra)

    def _ra_dec_2_alt_az(self):
        ra = self.ra * 15
        hour_angle = self._get_siderial_time() - ra
        hour_angle %= 360
        hour_angle = math.radians(hour_angle)
        dec = math.radians(self.dec)
        latitude = math.radians(self.latitude)

        sin_alt = math.sin(dec) * math.sin(latitude) + math.cos(dec) * math.cos(latitude) * math.cos(hour_angle)
        alt = math.asin(sin_alt)
        self.alt = math.degrees(alt)

        b1 = math.sin(dec) - math.sin(alt) * math.sin(latitude)
        b2 = math.cos(alt) * math.cos(latitude)
        cos_az = b1 / b2
        az = math.degrees(math.acos(cos_az))
        if math.sin(hour_angle) < 0:
            self.az = az
        else:
            self.az = 360 - az
        pass
