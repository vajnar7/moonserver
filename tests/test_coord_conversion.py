import unittest
from datetime import datetime, timezone

from telescope import convert_radec_to_az_el


class CoordConversionTests(unittest.TestCase):
    def test_returns_elevation_and_azimuth_in_expected_range(self):
        result = convert_radec_to_az_el(
            ra_deg=0.0,
            dec_deg=0.0,
            latitude_deg=45.0,
            longitude_deg=0.0,
            utc_time=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        )

        azimuth, elevation = result

        self.assertGreaterEqual(azimuth, 0.0)
        self.assertLess(azimuth, 360.0)
        self.assertGreaterEqual(elevation, -90.0)
        self.assertLessEqual(elevation, 90.0)


if __name__ == "__main__":
    unittest.main()
