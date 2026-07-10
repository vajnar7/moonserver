import unittest
from datetime import datetime, timezone

from telescope import (
    convert_radec_to_az_el,
    degrees_to_dms,
    degrees_to_hms,
    dms_to_degrees,
    hms_to_degrees,
)


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

    def test_ra_helpers_convert_between_hms_and_degrees(self):
        self.assertAlmostEqual(hms_to_degrees(12, 30, 0), 187.5)
        self.assertEqual(degrees_to_hms(187.5), (12, 30, 0.0))

    def test_dec_helpers_convert_between_dms_and_degrees(self):
        self.assertAlmostEqual(dms_to_degrees(12, 30, 0), 12.5)
        self.assertEqual(degrees_to_dms(12.5), (12, 30, 0.0))


if __name__ == "__main__":
    unittest.main()
