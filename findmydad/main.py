import datetime
import logging
import os
import typing

from findmydad.config import load_config
from findmydad.fetch_reports import Report, fetch_reports
from findmydad.geofences import Geofence, GeofenceManager
from findmydad.notify import send_sms

logger = logging.getLogger(__name__)


class Violation(typing.TypedDict):
    lat: float
    lon: float
    timestamp: datetime.datetime
    geofence: Geofence


def all_violations(reports: list[Report], fences: GeofenceManager) -> list[Violation]:
    violations = []
    for report in reports:
        violated_fences = fences.violations(
            lat=report["lat"],
            lon=report["lon"],
            timestamp=report["timestamp"],
        )
        for fence in violated_fences:
            violations.append(
                {
                    "lat": report["lat"],
                    "lon": report["lon"],
                    "timestamp": report["timestamp"],
                    "geofence": fence,
                }
            )

    return violations


def _google_maps_info(lat: float, lon: float) -> str:
    # can't send URLs with textbelt :(
    # return f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
    return f"{lat},{lon}"


def summarize_violations(violations: list[Violation]) -> str:
    violation = max(violations, key=lambda x: x["timestamp"])
    return f"At {violation['timestamp']}, Dad was at {_google_maps_info(violation['lat'], violation['lon'])} "


def main():
    logging.basicConfig(level=logging.DEBUG)
    config = load_config(os.getenv("FINDMYDAD_CONFIG"))
    for key, value in config.items():
        logger.debug(
            f"{key}: {value[:10] if isinstance(value, (str, bytes)) else value}..."
        )
    fence_manager = GeofenceManager(config["GEOFENCES_URL"])
    reports = fetch_reports(
        config["PLIST_BYTES"],
        anisette_url=config["ANISETTE_URL"],
        account_json=config["ACCOUNT_JSON"],
    )
    violations = all_violations(reports, fence_manager)
    logger.info(f"Found {len(violations)} violations")
    if violations:
        message = summarize_violations(violations)
        logger.info("message: %s", message)
        if not os.getenv("TEST"):
            for phone in config["PHONE_NUMBERS"]:
                logger.debug(f"Sending SMS to {phone}")
                send_sms(
                    phone_number=phone,
                    message=message,
                    api_key=config["TEXTBELT_API_KEY"],
                )


if __name__ == "__main__":
    main()
