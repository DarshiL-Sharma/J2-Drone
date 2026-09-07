import math

EARTH_RADIUS_M = 6378137.0

def latlng_to_north_east(base_lat, base_lng, target_lat, target_lng):
    """Equirectangular approximation — fine for the few-km ranges an SOS dispatch involves."""
    lat_rad = math.radians(base_lat)
    north = math.radians(target_lat - base_lat) * EARTH_RADIUS_M
    east = math.radians(target_lng - base_lng) * EARTH_RADIUS_M * math.cos(lat_rad)
    return north, east