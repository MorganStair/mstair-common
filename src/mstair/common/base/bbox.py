# File: python/plib_/base/bbox.py

from __future__ import annotations

from math import atan2, cos, floor, log10, radians, sin, sqrt


class BBox:
    EARTH_RADIUS_MI = 3958.8  # Earth's radius in miles
    FT_TO_MI = 5280.0  # Feet per mile
    MAX_PRECISION = 50.0 / FT_TO_MI  # 50 feet in miles

    def __init__(self, north: float, south: float, east: float, west: float):
        self.north = north  # max_lat
        self.south = south  # min_lat
        self.east = east  # max_lng
        self.west = west  # min_lng

    @staticmethod
    def from_cwh(c_lat: float, c_lng: float, w_mi: float, h_mi: float) -> BBox:
        hw = w_mi / 2
        hh = h_mi / 2

        d_lat = BBox._mi_to_lat_delta(hh)
        d_lng = BBox._mi_to_lng_delta(c_lat, hw)

        return BBox(c_lat + d_lat, c_lat - d_lat, c_lng + d_lng, c_lng - d_lng)

    def w(self):
        """Calculates the width of the bbox in miles."""
        return self._hav_dist(self.south, self.west, self.south, self.east)

    def h(self):
        """Calculates the height of the bbox in miles."""
        return self._hav_dist(self.south, self.west, self.north, self.west)

    def area(self):
        """Calculates the approximate area of the bbox in square miles."""
        return self.w() * self.h()

    def ctr(self):
        """Returns the center of the bbox as (lat, lng)."""
        return (self.south + self.north) / 2, (self.west + self.east) / 2

    def google_maps_url(self):
        """Returns a Google Maps URL for the bbox with the appropriate zoom level.

        Zoom calculation:
        - The zoom level is calculated based on the width of the bounding box in miles.
        - The Google Maps zoom level ranges from 1 (world view) to 21+ (building view).
        - We estimate the zoom level using a formula that inversely correlates the bounding box width to zoom.
        The smaller the width, the higher the zoom level.
        """
        c_lat, c_lng = self.ctr()
        width_miles = self.w()
        zoom = min(max(int(15 - log10(width_miles)), 1), 21)
        return f"https://www.google.com/maps/@{c_lat},{c_lng},{zoom}z"

    def __str__(self):
        """Returns a formatted string with center coordinates and dimensions."""
        c_lat, c_lng = self.ctr()
        precision = BBox.decimal_places(BBox.MAX_PRECISION)

        w = round(self.w(), precision)  # Dynamically round width based on precision
        h = round(self.h(), precision)

        # Round center to calculated decimal places (based on 50 feet)
        c_lat = round(c_lat, precision)
        c_lng = round(c_lng, precision)

        return f"ctr:{c_lat},{c_lng}, w:{w} mi, h:{h} mi"

    @staticmethod
    def _hav_dist(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculates the great-circle distance between two points on Earth."""
        lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])

        dlat = lat2 - lat1
        dlng = lng2 - lng1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return BBox.EARTH_RADIUS_MI * c

    @staticmethod
    def _mi_to_lat_delta(mi: float) -> float:
        """Converts a distance in miles to a change in latitude."""
        return mi / BBox.EARTH_RADIUS_MI * (180 / 3.141592653589793)

    @staticmethod
    def _mi_to_lng_delta(lat: float, mi: float) -> float:
        """Converts a distance in miles to a change in longitude."""
        radius_at_lat = BBox.EARTH_RADIUS_MI * cos(radians(lat))
        return (mi / radius_at_lat) * (180 / 3.141592653589793)

    @staticmethod
    def decimal_places(precision: float):
        """Calculates how many decimal places are needed based on the precision in miles."""
        if precision <= 0:
            return 0
        return max(0, -floor(log10(precision)))


if __name__ == "__main__":
    import unittest

    class TestBBox(unittest.TestCase):
        def test_w(self):
            bbox = BBox(28.8333, 28.6667, -97.8333, -98.1667)
            self.assertAlmostEqual(bbox.w(), 20.21, places=2)

        def test_h(self):
            bbox = BBox(28.8333, 28.6667, -97.8333, -98.1667)
            self.assertAlmostEqual(bbox.h(), 11.51, places=2)

        def test_precision(self):
            self.assertEqual(BBox.decimal_places(BBox.MAX_PRECISION), 3)  # pyright: ignore[reportPrivateUsage]

    unittest.main()

# End of file: python/plib_/base/bbox.py
