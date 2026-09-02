"""Media intelligence: Exif metadata, camera details, GPS extraction, and reverse geocoding."""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from rudra_osint.config import USER_AGENT


@dataclass
class GPSInfo:
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    maps_url: str = ""
    osm_url: str = ""
    resolved_address: str = ""


@dataclass
class MediaIntel:
    file_path: str
    file_name: str
    file_size_bytes: int
    file_type: str
    camera_make: str = ""
    camera_model: str = ""
    lens_model: str = ""
    software: str = ""
    datetime_original: str = ""
    exposure_time: str = ""
    f_number: str = ""
    iso_speed: str = ""
    focal_length: str = ""
    gps: Optional[GPSInfo] = None
    all_metadata: dict[str, str] = field(default_factory=dict)
    reverse_search_links: dict[str, str] = field(default_factory=dict)


def _convert_to_degrees(value) -> Optional[float]:
    """Convert GPS coordinates (DMS tuple) to decimal degrees."""
    try:
        if isinstance(value, (int, float)):
            return float(value)
        d = float(value[0])
        m = float(value[1])
        s = float(value[2])
        return d + (m / 60.0) + (s / 3600.0)
    except Exception:
        return None


def _reverse_geocode(lat: float, lon: float) -> str:
    """Reverse geocode decimal coordinates to an address via OpenStreetMap Nominatim."""
    url = f"https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={lat}&lon={lon}"
    req = urllib.request.Request(url, headers={"User-Agent": f"RudraOSINT/1.0 ({USER_AGENT})"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("display_name", "")
    except Exception:
        return ""


def analyze_media_file(file_path_str: str) -> Optional[MediaIntel]:
    """Extract metadata, camera parameters, and GPS coordinates from an image or video file."""
    path = Path(file_path_str).resolve()
    if not path.is_file():
        return None

    intel = MediaIntel(
        file_path=str(path),
        file_name=path.name,
        file_size_bytes=path.stat().st_size,
        file_type=path.suffix.lower(),
    )

    # Reverse image search URLs (using filename/image hash helpers)
    intel.reverse_search_links = {
        "Google Lens": "https://lens.google.com/",
        "Yandex Visual": "https://yandex.com/images/search?rpt=imageview",
        "TinEye": "https://tineye.com/",
        "Bing Visual Search": "https://www.bing.com/visualsearch",
    }

    # Try extracting Exif via PIL / Pillow if available, otherwise read standard headers
    try:
        from PIL import ExifTags, Image

        with Image.open(path) as img:
            exif = img._getexif()
            if exif:
                for tag_id, val in exif.items():
                    tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                    intel.all_metadata[tag_name] = str(val)

                intel.camera_make = intel.all_metadata.get("Make", "")
                intel.camera_model = intel.all_metadata.get("Model", "")
                intel.software = intel.all_metadata.get("Software", "")
                intel.datetime_original = intel.all_metadata.get("DateTimeOriginal", intel.all_metadata.get("DateTime", ""))
                intel.lens_model = intel.all_metadata.get("LensModel", "")
                intel.iso_speed = str(intel.all_metadata.get("ISOSpeedRatings", ""))
                intel.exposure_time = str(intel.all_metadata.get("ExposureTime", ""))
                intel.f_number = str(intel.all_metadata.get("FNumber", ""))
                intel.focal_length = str(intel.all_metadata.get("FocalLength", ""))

                # GPS Tags extraction
                gps_info_raw = exif.get(34853)  # 34853 is GPSInfo tag
                if gps_info_raw:
                    gps_tags = {}
                    for t in gps_info_raw:
                        sub_tag = ExifTags.GPSTAGS.get(t, str(t))
                        gps_tags[sub_tag] = gps_info_raw[t]

                    lat_raw = gps_tags.get("GPSLatitude")
                    lat_ref = gps_tags.get("GPSLatitudeRef", "N")
                    lon_raw = gps_tags.get("GPSLongitude")
                    lon_ref = gps_tags.get("GPSLongitudeRef", "E")

                    if lat_raw and lon_raw:
                        lat = _convert_to_degrees(lat_raw)
                        lon = _convert_to_degrees(lon_raw)
                        if lat is not None and lon is not None:
                            if lat_ref.upper() == "S":
                                lat = -lat
                            if lon_ref.upper() == "W":
                                lon = -lon

                            maps_url = f"https://www.google.com/maps?q={lat:.6f},{lon:.6f}"
                            osm_url = f"https://www.openstreetmap.org/?mlat={lat:.6f}&mlon={lon:.6f}"
                            address = _reverse_geocode(lat, lon)

                            intel.gps = GPSInfo(
                                latitude=lat,
                                longitude=lon,
                                maps_url=maps_url,
                                osm_url=osm_url,
                                resolved_address=address,
                            )
    except Exception:
        pass

    return intel
