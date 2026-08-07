import unittest
from datetime import datetime, timezone

from app import app, start_track_thread, stop_track_thread
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

    def test_getastrodata_returns_readable_coordinates(self):
        client = app.test_client()
        response = client.post("/command/getastrodata")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        polaris = payload["Polaris"]

        expected_ra = degrees_to_hms(37.95456067)
        expected_dec = degrees_to_dms(89.26410897)

        self.assertEqual(
            polaris["ra"],
            {"hours": expected_ra[0], "minutes": expected_ra[1], "seconds": expected_ra[2]},
        )
        self.assertEqual(
            polaris["dec"],
            {"degrees": expected_dec[0], "minutes": expected_dec[1], "seconds": expected_dec[2]},
        )

    def test_stop_track_thread_stops_running_tracker(self):
        stop_track_thread()
        start_track_thread()

        self.assertIsNotNone(app.track_thread)
        self.assertTrue(app.track_thread.is_alive())

        stop_track_thread()
        app.track_thread.join(timeout=2)

        self.assertFalse(app.track_thread.is_alive())


if __name__ == "__main__":
    unittest.main()
